from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, replace
import re
import time
from typing import cast

from pydantic import BaseModel, Field

from app.models.rfp import ProjectFile
from app.services.llm_service import LLMConfigurationError, LLMResponseError, LLMService
from app.services.prompts import (
    PROJECT_SUMMARY_SYSTEM_PROMPT,
    REQUIREMENTS_SYSTEM_PROMPT,
    build_project_summary_user_prompt,
    build_requirements_user_prompt,
)

SUMMARY_KEYWORDS = (
    "사업 개요",
    "사업개요",
    "사업 목적",
    "사업목적",
    "사업 내용",
    "사업내용",
    "과업 개요",
    "과업개요",
    "과업 내용",
    "과업내용",
    "추진 배경",
    "추진배경",
    "목적",
    "범위",
)
REQUIREMENT_KEYWORDS = (
    "요구사항",
    "요구 사항",
    "기능 요구",
    "기능요구",
    "비기능",
    "상세 요구",
    "세부 요구",
    "세부내용",
    "제안요청내용",
    "구축 범위",
    "필수 사항",
    "필수사항",
    "과업 내용",
    "과업내용",
)
EVALUATION_KEYWORDS = (
    "평가 항목",
    "평가항목",
    "배점",
    "평가 기준",
    "평가기준",
    "심사",
    "정량",
    "정성",
    "선정 기준",
    "선정기준",
)

SECTION_ROLE_PRIORITIES: dict[str, tuple[str, ...]] = {
    "summary": ("notice", "rfp", "sow", "requirements", "other"),
    "requirements": ("requirements", "rfp", "sow", "notice", "other"),
    "evaluation": ("notice", "rfp", "sow", "requirements", "other"),
}

SECTION_LIMITS = {"summary": 8, "requirements": 50, "evaluation": 8}
SECTION_CONTEXT_CHAR_LIMITS = {"summary": 900, "requirements": 1000, "evaluation": 900}
SECTION_TOTAL_CONTEXT_CHAR_BUDGETS = {"summary": 7000, "requirements": 12000, "evaluation": 7000}
REQUIREMENT_BATCH_CONTEXT_CHAR_BUDGET = 5_200
REQUIREMENT_BATCH_MAX_COMPLETION_TOKENS = 6_000
REQUIREMENT_MAX_ITEMS = 200

REQUIREMENT_SECTION_HEADING_RE = re.compile(r"(\d+\)\s*[^\n]{1,80}?요구사항)")
REQUIREMENT_START_RE = re.compile(r"(?=요구사항\s*번호\s*)")
REQUIREMENT_NO_RE = re.compile(
    r"요구사항\s*번호\s*([\s\S]{1,80}?)(?=요구사항\s*명칭|요구사항\s*상세설명|요구사항상세설명|정의|세부내용|산출물|$)"
)
REQUIREMENT_NAME_RE = re.compile(
    r"요구사항\s*명칭\s*([\s\S]{1,120}?)(?=요구사항\s*상세설명|요구사항상세설명|정의|세부내용|산출물|$)"
)
BULLET_LINE_RE = re.compile(r"^(?P<indent>\s*)(?P<marker>[•◦○●■□▪❍∙·\-–—])\s*(?P<content>.*)$")


class RfpExtractionError(RuntimeError):
    def __init__(self, message: str, *, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class FileChunkBundle:
    project_file: ProjectFile
    raw_text: str
    chunks: list[dict]


@dataclass(frozen=True)
class RequirementCandidate:
    bundle_index: int
    project_file: ProjectFile
    page_start: int | None
    page_end: int | None
    chunk_index: int
    chunk_end: int
    segment_index: int
    section_heading: str
    requirement_no: str
    requirement_name: str
    text_content: str


@dataclass(frozen=True)
class RequirementBatch:
    batch_index: int
    batch_label: str
    context: str
    candidate_count: int
    source_labels: list[str]


class StructuredProjectSummary(BaseModel):
    business_overview: str = ""
    scope: str = ""
    budget: str = ""
    submission_period_and_method: str = ""


class StructuredRequirement(BaseModel):
    requirement_no: str = ""
    name: str = ""
    definition: str = ""
    details: str = ""


class StructuredRequirementExtraction(BaseModel):
    requirements: list[StructuredRequirement] = Field(default_factory=list)


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    lines = [line.strip() for line in value.replace("\r\n", "\n").splitlines()]
    return "\n".join(line for line in lines if line).strip()


def _normalize_inline(value: str | None) -> str:
    return _normalize_text(value).replace("\n", " ").strip()


def _split_markdown_items(value: str | None) -> list[str]:
    normalized = _normalize_text(value)
    if not normalized:
        return []

    items: list[str] = []
    for raw_line in normalized.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = re.sub(r"^[•◦○●■□▪❍\-]+\s*", "", line)
        fragments = [fragment.strip() for fragment in re.split(r"\s*;\s*", line) if fragment.strip()]
        if fragments:
            items.extend(fragments)
        else:
            items.append(line)
    return items


def _format_summary_section(value: str | None, *, prefer_bullets: bool = False) -> str:
    items = _split_markdown_items(value)
    if not items:
        return "(없음)"
    if prefer_bullets or len(items) > 1:
        return "\n".join(f"- {item}" for item in items)
    return items[0]


def _format_requirement_details(value: str | None) -> str:
    if not value:
        return ""

    raw_lines = value.replace("\r\n", "\n").replace("\r", "\n").splitlines()
    normalized_lines: list[str] = []
    saw_bullet = False

    for raw_line in raw_lines:
        if not raw_line.strip():
            if normalized_lines and normalized_lines[-1] != "":
                normalized_lines.append("")
            continue

        bullet_match = BULLET_LINE_RE.match(raw_line.rstrip())
        if bullet_match:
            saw_bullet = True
            indent = bullet_match.group("indent") or ""
            marker = bullet_match.group("marker")
            content = re.sub(r"\s+", " ", bullet_match.group("content")).strip()
            if not content:
                continue
            indent_level = 0 if len(indent) <= 1 else 1
            normalized_lines.append(f"{'  ' * indent_level}{marker} {content}")
            continue

        compact = re.sub(r"\s+", " ", raw_line.strip())
        if compact:
            normalized_lines.append(compact)

    while normalized_lines and normalized_lines[-1] == "":
        normalized_lines.pop()

    if not normalized_lines:
        return ""
    if saw_bullet:
        return "\n".join(normalized_lines)

    items = _split_markdown_items("\n".join(normalized_lines))
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return "\n".join(f"- {item}" for item in items)


def _build_project_summary_markdown(summary: StructuredProjectSummary) -> str:
    return "\n\n".join(
        [
            "# 사업 개요",
            _format_summary_section(summary.business_overview),
            "# 과업 범위",
            _format_summary_section(summary.scope, prefer_bullets=True),
            "# 사업비",
            _format_summary_section(summary.budget),
            "# 제안서 제출 기간 및 제출 방법",
            _format_summary_section(summary.submission_period_and_method, prefer_bullets=True),
        ]
    ).strip()


def _role_rank(role: str, section: str) -> int:
    try:
        return SECTION_ROLE_PRIORITIES[section].index(role)
    except ValueError:
        return len(SECTION_ROLE_PRIORITIES[section])


def _chunk_label(project_file: ProjectFile, chunk: dict) -> str:
    page_start = chunk.get("page_start")
    page_end = chunk.get("page_end")
    role = project_file.role
    if page_start and page_end:
        if page_start == page_end:
            return f"{project_file.filename} | role={role} | p.{page_start}"
        return f"{project_file.filename} | role={role} | p.{page_start}-{page_end}"
    return f"{project_file.filename} | role={role}"


def _score_chunk(section: str, project_file: ProjectFile, chunk: dict) -> int:
    text = chunk["text_content"].lower()
    keywords = {
        "summary": SUMMARY_KEYWORDS,
        "requirements": REQUIREMENT_KEYWORDS,
        "evaluation": EVALUATION_KEYWORDS,
    }[section]
    score = sum(5 for keyword in keywords if keyword.lower() in text)
    score += max(0, 5 - _role_rank(project_file.role, section))
    route_label = (chunk.get("route_label") or "").lower()
    if section == "requirements" and route_label in {"requirements", "general"}:
        score += 2
    if section == "evaluation" and route_label == "evaluation":
        score += 3
    if section == "summary" and route_label in {"summary", "overview", "general"}:
        score += 2
    if section == "requirements" and re.search(r"\b\d+(?:\.\d+)*\b", chunk["text_content"]):
        score += 1
    if section == "evaluation" and re.search(r"\d+(?:\.\d+)?\s*(?:점|%)", chunk["text_content"]):
        score += 3
    return score


def _select_context(section: str, bundles: list[FileChunkBundle]) -> str:
    scored: list[tuple[int, int, int, ProjectFile, dict]] = []
    for bundle_index, bundle in enumerate(bundles):
        for chunk in bundle.chunks:
            scored.append(
                (
                    _score_chunk(section, bundle.project_file, chunk),
                    bundle_index,
                    chunk["chunk_index"],
                    bundle.project_file,
                    chunk,
                )
            )

    scored.sort(key=lambda row: (-row[0], row[1], row[2]))
    selected = [row for row in scored if row[0] > 0][: SECTION_LIMITS[section]]
    if not selected:
        selected = scored[: SECTION_LIMITS[section]]

    lines: list[str] = []
    total_context_chars = 0
    total_context_budget = SECTION_TOTAL_CONTEXT_CHAR_BUDGETS[section]
    for _, _, _, project_file, chunk in selected:
        remaining_budget = total_context_budget - total_context_chars
        if remaining_budget <= 0:
            break
        chunk_text = chunk["text_content"][: SECTION_CONTEXT_CHAR_LIMITS[section]]
        chunk_text = chunk_text[:remaining_budget].strip()
        if not chunk_text:
            continue
        lines.append(f"[{_chunk_label(project_file, chunk)} | chunk={chunk['chunk_index']}]")
        lines.append(chunk_text)
        lines.append("")
        total_context_chars += len(chunk_text)
    return "\n".join(lines).strip()


def _clean_requirement_fragment(value: str) -> str:
    normalized = _normalize_text(value)
    if not normalized:
        return ""
    normalized = re.sub(r"^(?:-\s*\d+\s*-\s*)+", "", normalized)
    return normalized.strip()


def _extract_requirement_section_heading(value: str) -> str:
    match = REQUIREMENT_SECTION_HEADING_RE.search(value)
    if not match:
        return ""
    return _normalize_inline(match.group(1))


def _extract_requirement_identity(value: str) -> tuple[str, str]:
    requirement_no_match = REQUIREMENT_NO_RE.search(value)
    name_match = REQUIREMENT_NAME_RE.search(value)
    requirement_no = _normalize_inline(requirement_no_match.group(1) if requirement_no_match else "")
    requirement_name = _normalize_inline(name_match.group(1) if name_match else "")
    return requirement_no, requirement_name


def _looks_like_requirement_payload(value: str) -> bool:
    normalized = _clean_requirement_fragment(value)
    if not normalized:
        return False
    if REQUIREMENT_START_RE.search(normalized):
        return True
    if any(marker in normalized for marker in ("요구사항 상세설명", "요구사항상세설명", "세부내용", "정의", "산출물")):
        return True
    if REQUIREMENT_SECTION_HEADING_RE.search(normalized):
        return True
    return False


def _parse_requirement_segments(value: str) -> tuple[str, list[tuple[str, str, str, str]]]:
    normalized = _clean_requirement_fragment(value)
    if not normalized:
        return "", []

    section_heading = _extract_requirement_section_heading(normalized)
    matches = list(REQUIREMENT_START_RE.finditer(normalized))
    if not matches:
        requirement_no, requirement_name = _extract_requirement_identity(normalized)
        if any((section_heading, requirement_no, requirement_name)) and _looks_like_requirement_payload(normalized):
            return "", [(section_heading, requirement_no, requirement_name, normalized)]
        return normalized, []

    prefix = normalized[: matches[0].start()].strip()
    segments: list[tuple[str, str, str, str]] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
        segment = normalized[start:end].strip()
        if section_heading and section_heading not in segment[: len(section_heading) + 40]:
            segment = f"{section_heading}\n{segment}"
        segment = _clean_requirement_fragment(segment)
        if not segment:
            continue
        requirement_no, requirement_name = _extract_requirement_identity(segment)
        segments.append((section_heading, requirement_no, requirement_name, segment))
    return prefix, segments


def _is_requirement_candidate_page(
    project_file: ProjectFile,
    page_text: str,
) -> bool:
    normalized = _clean_requirement_fragment(page_text)
    if not normalized:
        return False

    has_requirement_number = "요구사항 번호" in normalized
    has_requirement_heading = bool(REQUIREMENT_SECTION_HEADING_RE.search(normalized))
    has_detail_markers = any(
        marker in normalized
        for marker in ("요구사항 상세설명", "요구사항상세설명", "세부내용", "정의")
    )
    is_requirement_index_page = (
        "요구사항 목록" in normalized
        and "요구사항 번호" in normalized
        and not has_detail_markers
    )
    if is_requirement_index_page:
        return False

    if has_requirement_number and has_detail_markers:
        return True
    if has_requirement_heading and has_detail_markers and project_file.role in {"requirements", "rfp", "sow"}:
        return True
    return False


def _build_requirement_candidates(bundles: list[FileChunkBundle]) -> list[RequirementCandidate]:
    candidates: list[RequirementCandidate] = []
    for bundle_index, bundle in enumerate(bundles):
        page_groups: dict[int, list[dict]] = {}
        for chunk in bundle.chunks:
            page_number = chunk.get("page_start") or 0
            page_groups.setdefault(page_number, []).append(chunk)

        active_candidate: RequirementCandidate | None = None
        for page_number in sorted(page_groups):
            page_chunks = page_groups[page_number]
            ordered_chunks = sorted(page_chunks, key=lambda chunk: chunk["chunk_index"])
            page_text = "\n".join(
                fragment
                for fragment in (_clean_requirement_fragment(chunk["text_content"]) for chunk in ordered_chunks)
                if fragment
            ).strip()
            if not page_text:
                continue

            first_chunk_index = ordered_chunks[0]["chunk_index"]
            last_chunk_index = ordered_chunks[-1]["chunk_index"]
            prefix, split_segments = _parse_requirement_segments(page_text)

            if split_segments:
                if active_candidate and prefix and _should_attach_requirement_continuation(active_candidate, prefix):
                    active_candidate = _append_requirement_continuation(
                        active_candidate,
                        prefix,
                        page_end=page_number or None,
                        chunk_end=last_chunk_index,
                    )
                if active_candidate:
                    candidates.append(active_candidate)
                    active_candidate = None

                for segment_index, (section_heading, requirement_no, requirement_name, text_content) in enumerate(
                    split_segments,
                    start=1,
                ):
                    if not text_content or not any((section_heading, requirement_no, requirement_name)):
                        continue
                    candidate = RequirementCandidate(
                        bundle_index=bundle_index,
                        project_file=bundle.project_file,
                        page_start=page_number or None,
                        page_end=page_number or None,
                        chunk_index=first_chunk_index,
                        chunk_end=last_chunk_index,
                        segment_index=segment_index,
                        section_heading=section_heading,
                        requirement_no=requirement_no,
                        requirement_name=requirement_name,
                        text_content=text_content,
                    )
                    if segment_index < len(split_segments):
                        candidates.append(candidate)
                    else:
                        active_candidate = candidate
                continue

            if active_candidate and _should_attach_requirement_continuation(active_candidate, page_text):
                active_candidate = _append_requirement_continuation(
                    active_candidate,
                    page_text,
                    page_end=page_number or None,
                    chunk_end=last_chunk_index,
                )
                continue

            if not _is_requirement_candidate_page(bundle.project_file, page_text):
                if active_candidate:
                    candidates.append(active_candidate)
                    active_candidate = None
                continue

            section_heading = _extract_requirement_section_heading(page_text)
            requirement_no, requirement_name = _extract_requirement_identity(page_text)
            if not any((section_heading, requirement_no, requirement_name)):
                if active_candidate:
                    candidates.append(active_candidate)
                    active_candidate = None
                continue

            if active_candidate:
                candidates.append(active_candidate)
            active_candidate = RequirementCandidate(
                bundle_index=bundle_index,
                project_file=bundle.project_file,
                page_start=page_number or None,
                page_end=page_number or None,
                chunk_index=first_chunk_index,
                chunk_end=last_chunk_index,
                segment_index=1,
                section_heading=section_heading,
                requirement_no=requirement_no,
                requirement_name=requirement_name,
                text_content=page_text,
            )
        if active_candidate:
            candidates.append(active_candidate)
    return candidates


def _requirement_candidate_source_label(candidate: RequirementCandidate) -> str:
    if candidate.page_start and candidate.page_end:
        if candidate.page_start == candidate.page_end:
            page_label = f"p.{candidate.page_start}"
        else:
            page_label = f"p.{candidate.page_start}-{candidate.page_end}"
    else:
        page_label = "p.?"
    if candidate.chunk_index == candidate.chunk_end:
        chunk_label = f"chunk={candidate.chunk_index}"
    else:
        chunk_label = f"chunks={candidate.chunk_index}-{candidate.chunk_end}"
    return (
        f"{candidate.project_file.filename} | role={candidate.project_file.role} | "
        f"{page_label} | {chunk_label} | seg={candidate.segment_index}"
    )


def _should_attach_requirement_continuation(
    candidate: RequirementCandidate,
    continuation_text: str,
) -> bool:
    normalized = _clean_requirement_fragment(continuation_text)
    if not normalized:
        return False
    if REQUIREMENT_START_RE.search(normalized):
        return False
    if REQUIREMENT_SECTION_HEADING_RE.search(normalized[:120]):
        return False

    tail = candidate.text_content.rstrip()
    if tail.endswith((",", ":", ";", "/", "(", "·")):
        return True

    first_line = next((line.strip() for line in normalized.splitlines() if line.strip()), "")
    if not first_line:
        return False
    if BULLET_LINE_RE.match(first_line):
        return True
    if first_line.startswith(("※", "*")):
        return True
    return False


def _append_requirement_continuation(
    candidate: RequirementCandidate,
    continuation_text: str,
    *,
    page_end: int | None,
    chunk_end: int,
) -> RequirementCandidate:
    normalized = _clean_requirement_fragment(continuation_text)
    if not normalized:
        return candidate

    current_text = candidate.text_content.rstrip()
    first_line = next((line.strip() for line in normalized.splitlines() if line.strip()), "")
    if current_text.endswith((",", ":", ";", "/", "(", "·")):
        separator = ""
    elif first_line and BULLET_LINE_RE.match(first_line):
        separator = "\n"
    else:
        separator = "\n"

    return replace(
        candidate,
        page_end=page_end or candidate.page_end,
        chunk_end=chunk_end,
        text_content=f"{current_text}{separator}{normalized}".strip(),
    )


def _requirement_candidate_key(candidate: RequirementCandidate) -> str | None:
    requirement_no = _normalize_inline(candidate.requirement_no).casefold()
    requirement_name = _normalize_inline(candidate.requirement_name).casefold()
    section_heading = _normalize_inline(candidate.section_heading).casefold()
    if requirement_no and requirement_name:
        return f"{requirement_no}::{requirement_name}"
    if requirement_no and section_heading:
        return f"{section_heading}::{requirement_no}"
    if requirement_no and any(marker in requirement_no for marker in ("-", "①", "②", "③", "④", "⑤")):
        return requirement_no
    return None


def _prefer_requirement_candidate(
    current: RequirementCandidate,
    challenger: RequirementCandidate,
) -> RequirementCandidate:
    current_rank = _role_rank(current.project_file.role, "requirements")
    challenger_rank = _role_rank(challenger.project_file.role, "requirements")
    if challenger_rank < current_rank:
        return challenger
    if challenger_rank > current_rank:
        return current
    current_order = (current.bundle_index, current.page_start or 0, current.chunk_index, current.segment_index)
    challenger_order = (
        challenger.bundle_index,
        challenger.page_start or 0,
        challenger.chunk_index,
        challenger.segment_index,
    )
    return challenger if challenger_order < current_order else current


def _dedupe_requirement_candidates(
    candidates: list[RequirementCandidate],
) -> list[RequirementCandidate]:
    chosen_by_key: dict[str, RequirementCandidate] = {}
    passthrough: list[RequirementCandidate] = []
    for candidate in candidates:
        key = _requirement_candidate_key(candidate)
        if key is None:
            passthrough.append(candidate)
            continue
        existing = chosen_by_key.get(key)
        if existing is None:
            chosen_by_key[key] = candidate
            continue
        chosen_by_key[key] = _prefer_requirement_candidate(existing, candidate)

    deduped = [*passthrough, *chosen_by_key.values()]
    deduped.sort(
        key=lambda candidate: (
            candidate.bundle_index,
            candidate.page_start or 0,
            candidate.chunk_index,
            candidate.segment_index,
        )
    )
    return deduped


def _render_requirement_candidate(candidate: RequirementCandidate) -> str:
    label = _requirement_candidate_source_label(candidate)
    if candidate.requirement_no:
        label = f"{label} | no={candidate.requirement_no}"
    if candidate.requirement_name:
        label = f"{label} | name={candidate.requirement_name}"
    return f"[{label}]\n{candidate.text_content.strip()}"


def _make_requirement_batch(
    batch_index: int,
    batch_label: str,
    candidates: list[RequirementCandidate],
) -> RequirementBatch:
    rendered_candidates = [_render_requirement_candidate(candidate) for candidate in candidates]
    return RequirementBatch(
        batch_index=batch_index,
        batch_label=batch_label,
        context="\n\n".join(rendered_candidates).strip(),
        candidate_count=len(candidates),
        source_labels=[_requirement_candidate_source_label(candidate) for candidate in candidates],
    )


def _build_requirement_batches(bundles: list[FileChunkBundle]) -> list[RequirementBatch]:
    candidates = _dedupe_requirement_candidates(_build_requirement_candidates(bundles))
    if not candidates:
        return []

    batches: list[RequirementBatch] = []
    current_candidates: list[RequirementCandidate] = []
    current_chars = 0
    current_section_label = ""
    batch_index = 1

    for candidate in candidates:
        candidate_section_label = candidate.section_heading or "요구사항 일반"
        rendered = _render_requirement_candidate(candidate)
        needs_new_batch = bool(
            current_candidates
            and (
                candidate_section_label != current_section_label
                or current_chars + len(rendered) > REQUIREMENT_BATCH_CONTEXT_CHAR_BUDGET
            )
        )
        if needs_new_batch:
            batches.append(
                _make_requirement_batch(batch_index, current_section_label, current_candidates)
            )
            batch_index += 1
            current_candidates = []
            current_chars = 0

        if not current_candidates:
            current_section_label = candidate_section_label

        current_candidates.append(candidate)
        current_chars += len(rendered)

    if current_candidates:
        batches.append(_make_requirement_batch(batch_index, current_section_label, current_candidates))
    return batches


def _normalize_requirements(items: list[StructuredRequirement]) -> list[dict]:
    normalized: list[dict] = []
    seen_keys: set[str] = set()

    for item in items:
        requirement_no = _normalize_inline(item.requirement_no)
        name = _normalize_inline(item.name)
        definition = _normalize_text(item.definition)
        details = _format_requirement_details(item.details)
        if not any((requirement_no, name, definition, details)):
            continue

        dedupe_key = (requirement_no or name or definition[:120]).casefold()
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)
        normalized.append(
            {
                "requirement_no": requirement_no[:100],
                "name": name[:255],
                "definition": definition[:2000],
                "details": details[:6000],
            }
        )

    return normalized[:REQUIREMENT_MAX_ITEMS]


def _merge_raw_text(bundles: list[FileChunkBundle]) -> str:
    parts: list[str] = []
    for bundle in bundles:
        normalized = bundle.raw_text.strip()
        if not normalized:
            continue
        parts.append(f"[{bundle.project_file.filename} | role={bundle.project_file.role}]")
        parts.append(normalized)
        parts.append("")
    return "\n".join(parts).strip()


def _run_section_extraction(
    *,
    section_label: str,
    llm_service: LLMService,
    system_prompt: str,
    user_prompt: str,
    response_format: type[BaseModel],
    max_completion_tokens: int,
    trace_project_id: int | None = None,
    trace_kind: str | None = None,
    trace_metadata: dict[str, object] | None = None,
) -> BaseModel:
    last_error: Exception | None = None
    for attempt in range(1, 3):
        try:
            return cast(
                BaseModel,
                llm_service.parse_chat_completion(
                    model=llm_service.settings.openai_model_extraction,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    response_format=response_format,
                    max_completion_tokens=max_completion_tokens,
                    trace_project_id=trace_project_id,
                    trace_kind=trace_kind,
                    trace_metadata=trace_metadata,
                ),
            )
        except (LLMConfigurationError, LLMResponseError) as exc:
            last_error = exc
            message = str(exc)
            if "APITimeoutError" not in message or attempt == 2:
                if "APITimeoutError" in message:
                    raise RfpExtractionError(
                        f"{section_label} 추출 중 시간이 초과되었습니다. 선택 파일 수를 줄이거나 "
                        "OPENAI_TIMEOUT_SECONDS 값을 늘려 다시 시도해 주세요."
                    ) from exc
                raise RfpExtractionError(f"{section_label} 추출 실패: {message}") from exc
            time.sleep(1.5 * attempt)

    raise RfpExtractionError(f"{section_label} 추출 실패: {last_error}")


def extract_rfp_payload(
    *,
    bundles: list[FileChunkBundle],
    requirement_bundles: list[FileChunkBundle] | None = None,
    llm_service: LLMService,
) -> tuple[dict, list[dict], list[dict]]:
    if not bundles:
        raise RfpExtractionError("공고 파일이 없습니다.", status_code=422)

    raw_text = _merge_raw_text(bundles)
    if not raw_text:
        raise RfpExtractionError(
            "업로드한 파일에서 추출된 텍스트가 비어 있습니다. 스캔 PDF라면 OCR이 필요할 수 있습니다.",
            status_code=422,
        )

    effective_requirement_bundles = requirement_bundles or bundles
    summary_context = _select_context("summary", bundles)
    requirement_context = _select_context("requirements", effective_requirement_bundles)
    requirement_batches = _build_requirement_batches(effective_requirement_bundles)
    if not requirement_batches:
        fallback_context = requirement_context or raw_text[:12000]
        requirement_batches = [
            RequirementBatch(
                batch_index=1,
                batch_label="요구사항 전체",
                context=fallback_context,
                candidate_count=0,
                source_labels=[],
            )
        ]

    project_id = bundles[0].project_file.project_id
    file_ids = [bundle.project_file.id for bundle in bundles]
    summary_prompt_context = summary_context or raw_text[:12000]
    requirement_results: dict[int, StructuredRequirementExtraction] = {}

    with ThreadPoolExecutor(max_workers=1 + len(requirement_batches)) as executor:
        summary_future = executor.submit(
            _run_section_extraction,
            section_label="사업 개요",
            llm_service=llm_service,
            system_prompt=PROJECT_SUMMARY_SYSTEM_PROMPT,
            user_prompt=build_project_summary_user_prompt(context=summary_prompt_context),
            response_format=StructuredProjectSummary,
            max_completion_tokens=900,
            trace_project_id=project_id,
            trace_kind="rfp.summary",
            trace_metadata={
                "section": "summary",
                "selected_file_ids": file_ids,
                "bundle_count": len(bundles),
                "context_length": len(summary_prompt_context),
            },
        )
        future_to_batch = {
            executor.submit(
                _run_section_extraction,
                section_label=f"요구사항 배치 {batch.batch_index}",
                llm_service=llm_service,
                system_prompt=REQUIREMENTS_SYSTEM_PROMPT,
                user_prompt=build_requirements_user_prompt(
                    context=batch.context,
                    batch_label=f"{batch.batch_index}/{len(requirement_batches)} · {batch.batch_label}",
                ),
                response_format=StructuredRequirementExtraction,
                max_completion_tokens=REQUIREMENT_BATCH_MAX_COMPLETION_TOKENS,
                trace_project_id=project_id,
                trace_kind="rfp.requirements.batch",
                trace_metadata={
                    "section": "requirements",
                    "selected_file_ids": file_ids,
                    "bundle_count": len(bundles),
                    "batch_index": batch.batch_index,
                    "batch_count": len(requirement_batches),
                    "batch_label": batch.batch_label,
                    "candidate_count": batch.candidate_count,
                    "context_length": len(batch.context),
                },
            ): batch
            for batch in requirement_batches
        }
        for future in as_completed(future_to_batch):
            batch = future_to_batch[future]
            requirement_results[batch.batch_index] = cast(
                StructuredRequirementExtraction,
                future.result(),
            )
        summary = cast(StructuredProjectSummary, summary_future.result())

    requirement_items: list[StructuredRequirement] = []
    for batch in sorted(requirement_batches, key=lambda item: item.batch_index):
        requirement_items.extend(requirement_results[batch.batch_index].requirements)
    ocr_required = any(
        bundle.project_file.mime == "application/pdf" and len(bundle.raw_text.strip()) < 80
        for bundle in bundles
    )
    payload = {
        "status": "draft",
        "raw_text": raw_text,
        "project_summary_text": _build_project_summary_markdown(summary),
        "ocr_required": ocr_required,
        "eligibility_text": "",
        "submission_docs_text": "",
        "evaluation_overview_text": "",
        "format_rules_text": "",
        "deadline_iso": None,
        "contact_text": "",
        "notes_text": "",
        "source_file_path": None,
    }
    return (
        payload,
        _normalize_requirements(requirement_items),
        [],
    )
