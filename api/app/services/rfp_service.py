from __future__ import annotations

from dataclasses import dataclass
import re

from pydantic import BaseModel, Field

from app.models.rfp import ProjectFile
from app.services.llm_service import LLMConfigurationError, LLMResponseError, LLMService
from app.services.rfp_prompts import (
    EVALUATION_SYSTEM_PROMPT,
    EVALUATION_USER_PROMPT_TEMPLATE,
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
    project_summary_text: str = ""


class StructuredRequirement(BaseModel):
    requirement_no: str = ""
    name: str = ""
    definition: str = ""
    details: str = ""


class StructuredRequirementExtraction(BaseModel):
    requirements: list[StructuredRequirement] = Field(default_factory=list)


class StructuredEvaluation(BaseModel):
    item: str = ""
    score: str = ""
    notes: str = ""


class StructuredEvaluationExtraction(BaseModel):
    evaluation_items: list[StructuredEvaluation] = Field(default_factory=list)


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    lines = [line.strip() for line in value.replace("\r\n", "\n").splitlines()]
    return "\n".join(line for line in lines if line).strip()


def _normalize_inline(value: str | None) -> str:
    return _normalize_text(value).replace("\n", " ").strip()


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
                "details": details[:6000],
            }
        )

    return normalized[:80]


def _normalize_evaluation_items(items: list[StructuredEvaluation]) -> list[dict]:
    normalized: list[dict] = []
    seen_titles: set[str] = set()

    for item in items:
        title = _normalize_inline(item.item)
        score = _normalize_inline(item.score)
        notes = _normalize_text(item.notes)
        if not any((title, score, notes)):
            continue
        dedupe_key = (title or notes[:120]).casefold()
        if dedupe_key in seen_titles:
            continue
        seen_titles.add(dedupe_key)
        normalized.append({"item": title[:255], "score": score[:100], "notes": notes[:4000]})

    return normalized[:40]


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
    evaluation_context = _select_context("evaluation", bundles)

    try:
        summary = llm_service.parse_chat_completion(
            model=llm_service.settings.openai_model_extraction,
            system_prompt=PROJECT_SUMMARY_SYSTEM_PROMPT,
            user_prompt=PROJECT_SUMMARY_USER_PROMPT_TEMPLATE.format(context=summary_context or raw_text[:12000]),
            response_format=StructuredProjectSummary,
            max_completion_tokens=900,
        )
        requirement_result = llm_service.parse_chat_completion(
            model=llm_service.settings.openai_model_extraction,
            system_prompt=REQUIREMENTS_SYSTEM_PROMPT,
            user_prompt=REQUIREMENTS_USER_PROMPT_TEMPLATE.format(
                context=requirement_context or raw_text[:12000]
            ),
            response_format=StructuredRequirementExtraction,
            max_completion_tokens=2600,
        )
        evaluation_result = llm_service.parse_chat_completion(
            model=llm_service.settings.openai_model_extraction,
            system_prompt=EVALUATION_SYSTEM_PROMPT,
            user_prompt=EVALUATION_USER_PROMPT_TEMPLATE.format(
                context=evaluation_context or raw_text[:9000]
            ),
            response_format=StructuredEvaluationExtraction,
            max_completion_tokens=1800,
        )
    except (LLMConfigurationError, LLMResponseError) as exc:
        raise RfpExtractionError(str(exc)) from exc

    ocr_required = any(
        bundle.project_file.mime == "application/pdf" and len(bundle.raw_text.strip()) < 80
        for bundle in bundles
    )
    payload = {
        "status": "draft",
        "raw_text": raw_text,
        "project_summary_text": _normalize_text(summary.project_summary_text),
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
        _normalize_evaluation_items(evaluation_result.evaluation_items),
    )
