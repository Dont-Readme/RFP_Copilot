from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.evaluation import EvaluationItem
from app.models.outline import OutlineSection
from app.models.rfp import RfpRequirementItem
from app.services.llm_service import LLMConfigurationError, LLMResponseError, LLMService
from app.services.review_item_service import ReviewItemPayload, build_heading_text, merge_review_payloads


SECTION_REVIEW_SYSTEM_PROMPT = """
You review a Korean public proposal section and write short review items.

Rules:
- Review only the provided section and context.
- Focus on: missing evidence, missing quantitative detail, weak differentiation, unclear scope, or need for fresher search.
- Do not rewrite the section body.
- Return concise Korean comments only.
- If the section is already sufficient, return an empty list.
""".strip()


class SectionReviewError(RuntimeError):
    pass


class StructuredReviewItem(BaseModel):
    category: str = "missing_evidence"
    severity: str = "medium"
    comment: str = ""


class StructuredSectionReview(BaseModel):
    items: list[StructuredReviewItem] = Field(default_factory=list)


def _requirements_summary(requirements: list[RfpRequirementItem]) -> str:
    if not requirements:
        return "관련 요구사항 없음"
    return "\n".join(
        f"- {(requirement.name or requirement.requirement_no or '요구사항').strip()}: {(requirement.definition or requirement.details or '').strip()[:180]}"
        for requirement in requirements[:5]
    )


def _evaluation_summary(evaluation_items: list[EvaluationItem]) -> str:
    if not evaluation_items:
        return "관련 평가항목 없음"
    return "\n".join(
        f"- {(item.item or '평가항목').strip()}: {(item.notes or item.score or '').strip()[:160]}"
        for item in evaluation_items[:4]
    )


def _search_summary(search_snippets: list[str]) -> str:
    if not search_snippets:
        return "검색 결과 없음"
    return "\n".join(f"- {snippet[:220]}" for snippet in search_snippets[:4])


def review_section(
    *,
    llm_service: LLMService,
    section: OutlineSection,
    section_goal: str,
    draft_guidance: str,
    content_md: str,
    requirements: list[RfpRequirementItem],
    evaluation_items: list[EvaluationItem],
    search_snippets: list[str],
) -> list[ReviewItemPayload]:
    heading_text = build_heading_text(section)
    try:
        generated = llm_service.parse_chat_completion(
            model=llm_service.settings.openai_model_draft,
            system_prompt=SECTION_REVIEW_SYSTEM_PROMPT,
            user_prompt=f"""
Section heading: {heading_text}
Section goal:
{section_goal}

Draft guidance:
{draft_guidance}

Related requirements:
{_requirements_summary(requirements)}

Related evaluation items:
{_evaluation_summary(evaluation_items)}

Recent search findings:
{_search_summary(search_snippets)}

Draft section body:
{content_md or '본문 없음'}

Return structured review items only.
""".strip(),
            response_format=StructuredSectionReview,
            max_completion_tokens=900,
        )
    except (LLMConfigurationError, LLMResponseError) as exc:
        raise SectionReviewError(str(exc)) from exc

    items = [
        ReviewItemPayload(
            outline_section_id=section.id,
            section_heading_text=heading_text,
            question_text=item.comment.strip(),
            category=(item.category or "missing_evidence").strip() or "missing_evidence",
            severity=(item.severity or "medium").strip() or "medium",
            source_agent="reviewer",
        )
        for item in generated.items
        if item.comment.strip()
    ]
    return merge_review_payloads(items)
