from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import re
import time
from typing import cast

from pydantic import BaseModel, Field

from app.models.rfp import ProjectFile
from app.services.llm_service import LLMConfigurationError, LLMResponseError, LLMService
from app.services.rfp_prompts import (
    PROJECT_SUMMARY_SYSTEM_PROMPT,
    PROJECT_SUMMARY_USER_PROMPT_TEMPLATE,
    REQUIREMENTS_SYSTEM_PROMPT,
    REQUIREMENTS_USER_PROMPT_TEMPLATE,
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

SECTION_LIMITS = {"summary": 8, "requirements": 10, "evaluation": 8}
SECTION_CONTEXT_CHAR_LIMITS = {"summary": 900, "requirements": 1000, "evaluation": 900}


class RfpExtractionError(RuntimeError):
    def __init__(self, message: str, *, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class FileChunkBundle:
    project_file: ProjectFile
    raw_text: str
    chunks: list[dict]


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
    items = _split_markdown_items(value)
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
    for _, _, _, project_file, chunk in selected:
        lines.append(f"[{_chunk_label(project_file, chunk)} | chunk={chunk['chunk_index']}]")
        lines.append(chunk["text_content"][: SECTION_CONTEXT_CHAR_LIMITS[section]])
        lines.append("")
    return "\n".join(lines).strip()


def _normalize_requirements(items: list[StructuredRequirement]) -> list[dict]:
    normalized: list[dict] = []
    seen_keys: set[str] = set()

    for item in items:
        requirement_no = _normalize_inline(item.requirement_no)
        name = _normalize_inline(item.name)
        definition = _normalize_text(item.definition)
        details = _normalize_text(item.details)
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
                "details": _format_requirement_details(details)[:6000],
            }
        )

    return normalized[:80]


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

    summary_context = _select_context("summary", bundles)
    requirement_context = _select_context("requirements", bundles)
    extraction_specs = {
        "summary": {
            "section_label": "사업 개요",
            "system_prompt": PROJECT_SUMMARY_SYSTEM_PROMPT,
            "user_prompt": PROJECT_SUMMARY_USER_PROMPT_TEMPLATE.format(
                context=summary_context or raw_text[:12000]
            ),
            "response_format": StructuredProjectSummary,
            "max_completion_tokens": 900,
        },
        "requirements": {
            "section_label": "요구사항",
            "system_prompt": REQUIREMENTS_SYSTEM_PROMPT,
            "user_prompt": REQUIREMENTS_USER_PROMPT_TEMPLATE.format(
                context=requirement_context or raw_text[:12000]
            ),
            "response_format": StructuredRequirementExtraction,
            "max_completion_tokens": 2600,
        },
    }
    extracted_sections: dict[str, BaseModel] = {}
    with ThreadPoolExecutor(max_workers=len(extraction_specs)) as executor:
        future_to_section = {
            executor.submit(
                _run_section_extraction,
                section_label=spec["section_label"],
                llm_service=llm_service,
                system_prompt=spec["system_prompt"],
                user_prompt=spec["user_prompt"],
                response_format=spec["response_format"],
                max_completion_tokens=spec["max_completion_tokens"],
            ): section
            for section, spec in extraction_specs.items()
        }
        for future in as_completed(future_to_section):
            section = future_to_section[future]
            extracted_sections[section] = future.result()

    summary = cast(StructuredProjectSummary, extracted_sections["summary"])
    requirement_result = cast(
        StructuredRequirementExtraction, extracted_sections["requirements"]
    )
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
        _normalize_requirements(requirement_result.requirements),
        [],
    )
