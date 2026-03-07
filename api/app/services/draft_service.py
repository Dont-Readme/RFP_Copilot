from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.evaluation import EvaluationItem
from app.models.outline import OutlineSection
from app.models.rfp import RfpExtraction, RfpRequirementItem
from app.services.llm_service import LLMConfigurationError, LLMResponseError, LLMService
from app.services.review_item_service import merge_review_texts, strip_inline_review_items

DRAFT_SECTION_SYSTEM_PROMPT = """
You write one Korean public proposal section.

Rules:
- Write in a concrete, proposal-ready Korean style.
- Follow this flow whenever possible: background -> response direction -> execution plan -> expected effect.
- Use only information supported by the provided RFP summary, related requirements, evaluation items, company facts, and search findings.
- Do not invent numbers, certifications, customers, patents, or performance claims.
- Prefer specific nouns and execution detail over generic slogans.
- If critical detail is missing, keep the body clean and return missing points through `system_review_items`.
- Return Markdown only for the section body, without the heading line.
""".strip()


class DraftGenerationError(RuntimeError):
    pass


class StructuredDraftSection(BaseModel):
    content_md: str = ""
    system_review_items: list[str] = Field(default_factory=list)


def _rfp_summary(extraction: RfpExtraction) -> str:
    if extraction.project_summary_text:
        return extraction.project_summary_text
    return "구조화된 RFP 요약이 아직 비어 있습니다."


def _requirements_summary(requirements: list[RfpRequirementItem]) -> str:
    if not requirements:
        return "관련 요구사항 없음"
    lines = []
    for requirement in requirements[:5]:
        title = (requirement.name or requirement.requirement_no or "요구사항").strip()
        detail = (requirement.definition or requirement.details or "").strip()
        lines.append(f"- {title}: {detail[:220] if detail else '세부 내용 확인 필요'}")
    return "\n".join(lines)


def _evaluation_summary(evaluation_items: list[EvaluationItem]) -> str:
    if not evaluation_items:
        return "관련 평가항목 없음"
    lines = []
    for item in evaluation_items[:4]:
        title = (item.item or "평가항목").strip()
        note = (item.notes or item.score or "").strip()
        lines.append(f"- {title}: {note[:180] if note else '평가 포인트 확인 필요'}")
    return "\n".join(lines)


def _company_summary(company_facts: list[str]) -> str:
    if not company_facts:
        return "관련 회사 정보 없음"
    return "\n".join(f"- {fact}" for fact in company_facts[:5])


def _search_summary(search_context: list[str]) -> str:
    if not search_context:
        return "최신 검색 결과 없음"
    return "\n".join(f"- {item[:240]}" for item in search_context[:4])


def _paragraph_target(depth: int) -> str:
    if depth <= 1:
        return "3~5개 문단 또는 동등한 밀도의 markdown 목록"
    return "2~3개 문단 또는 동등한 밀도의 markdown 목록"


def generate_section_draft(
    *,
    llm_service: LLMService,
    project_name: str,
    section: OutlineSection,
    extraction: RfpExtraction,
    section_goal: str,
    draft_guidance: str,
    requirements: list[RfpRequirementItem],
    evaluation_items: list[EvaluationItem],
    company_facts: list[str],
    search_context: list[str],
) -> StructuredDraftSection:
    try:
        generated = llm_service.parse_chat_completion(
            model=llm_service.settings.openai_model_draft,
            system_prompt=DRAFT_SECTION_SYSTEM_PROMPT,
            user_prompt=f"""
Project name: {project_name}
Section heading: {section.display_label} {section.title}
Section depth: {section.depth}
Target length: {_paragraph_target(section.depth)}

Section goal:
{section_goal}

Draft guidance:
{draft_guidance}

Structured RFP summary:
{_rfp_summary(extraction)}

Related requirements:
{_requirements_summary(requirements)}

Related evaluation items:
{_evaluation_summary(evaluation_items)}

Company facts:
{_company_summary(company_facts)}

Recent search findings:
{_search_summary(search_context)}

Write the section body only.
If evidence is missing, keep the body conservative and return the missing points through `system_review_items`.
""".strip(),
            response_format=StructuredDraftSection,
            max_completion_tokens=1800,
        )
    except (LLMConfigurationError, LLMResponseError) as exc:
        raise DraftGenerationError(str(exc)) from exc

    content_md, inline_review_items = strip_inline_review_items(generated.content_md.strip())
    return StructuredDraftSection(
        content_md=content_md,
        system_review_items=merge_review_texts(generated.system_review_items, inline_review_items),
    )
