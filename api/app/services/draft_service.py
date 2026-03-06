from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.evaluation import EvaluationItem
from app.models.outline import OutlineSection
from app.models.retrieval import DocumentChunk
from app.models.rfp import RfpExtraction, RfpRequirementItem
from app.services.llm_service import LLMConfigurationError, LLMResponseError, LLMService
from app.services.retrieval_service import RetrievedChunk, format_retrieved_context

DRAFT_SECTION_SYSTEM_PROMPT = """
You write Korean proposal draft sections based only on verified RFP requirements and retrieved company materials.

Rules:
- Write concise, professional proposal prose in Korean.
- Use only information supported by the provided context.
- Do not invent numbers, certifications, clients, or capabilities.
- If a critical detail is missing, insert a line starting with `[확인 필요(시스템)]`.
- Return Markdown only for the body of the section, without the heading marker.
- Keep the section focused on the specific heading and evaluation intent.
""".strip()


class DraftGenerationError(RuntimeError):
    pass


class StructuredDraftSection(BaseModel):
    content_md: str = ""
    follow_up_questions: list[str] = Field(default_factory=list)


def _rfp_summary(
    extraction: RfpExtraction,
    requirements: list[RfpRequirementItem],
    evaluation_items: list[EvaluationItem],
) -> str:
    lines = []
    if extraction.project_summary_text:
        lines.append(f"- 사업 개요: {extraction.project_summary_text}")
    if requirements:
        lines.append("- 주요 요구사항:")
        for requirement in requirements[:8]:
            header = requirement.name or requirement.requirement_no or "무제 요구사항"
            detail = requirement.definition or requirement.details
            lines.append(f"  - {header}: {detail[:180] if detail else '세부 내용 확인 필요'}")
    if evaluation_items:
        lines.append("- 주요 평가항목:")
        for item in evaluation_items[:6]:
            score = item.score_text or (f"{item.weight:g}" if item.weight is not None else "")
            suffix = f" ({score})" if score else ""
            notes = item.description[:140] if item.description else ""
            lines.append(f"  - {item.title}{suffix}: {notes or '비고 없음'}")
    return "\n".join(lines) if lines else "구조화된 RFP 요약이 아직 비어 있습니다."


def _fallback_questions(section: OutlineSection, retrieved: list[RetrievedChunk]) -> list[str]:
    questions: list[str] = []
    if not retrieved:
        questions.append(f"'{section.title}' 섹션에 반영할 회사 자료 근거를 추가로 연결하거나 보강해 주세요.")
    if section.needs_search and len(retrieved) < 2:
        questions.append(f"'{section.title}' 섹션의 정량 근거 또는 사례 근거를 더 확보해 주세요.")
    return questions


def _build_user_prompt(
    *,
    project_name: str,
    section: OutlineSection,
    extraction: RfpExtraction,
    requirements: list[RfpRequirementItem],
    evaluation_items: list[EvaluationItem],
    retrieved: list[RetrievedChunk],
) -> str:
    return f"""
Project name: {project_name}
Section title: {section.title}
Section requires evidence search: {"yes" if section.needs_search else "no"}

Structured RFP summary:
{_rfp_summary(extraction, requirements, evaluation_items)}

Retrieved source context:
{format_retrieved_context(retrieved, max_items=4)}

Write the draft body for this section.
If evidence is weak or missing, clearly mark the missing point with `[확인 필요(시스템)]`.
Also return short follow-up questions for the user when more evidence or decisions are required.
""".strip()


def build_generated_draft(
    *,
    project_name: str,
    sections: list[OutlineSection],
    extraction: RfpExtraction,
    requirements: list[RfpRequirementItem],
    evaluation_items: list[EvaluationItem],
    retrieved_by_section: dict[int, list[RetrievedChunk]],
    llm_service: LLMService,
) -> tuple[str, list[str]]:
    lines = [f"# {project_name}"]
    questions: list[str] = []

    for section in sections:
        retrieved = retrieved_by_section.get(section.id, [])
        try:
            generated = llm_service.parse_chat_completion(
                model=llm_service.settings.openai_model_draft,
                system_prompt=DRAFT_SECTION_SYSTEM_PROMPT,
                user_prompt=_build_user_prompt(
                    project_name=project_name,
                    section=section,
                    extraction=extraction,
                    requirements=requirements,
                    evaluation_items=evaluation_items,
                    retrieved=retrieved,
                ),
                response_format=StructuredDraftSection,
                max_completion_tokens=1800,
            )
        except (LLMConfigurationError, LLMResponseError) as exc:
            raise DraftGenerationError(str(exc)) from exc

        lines.extend(["", f"## {section.title}"])
        content_md = generated.content_md.strip() or "[확인 필요(시스템)] 초안 생성 결과가 비어 있습니다."
        lines.append(content_md)

        section_questions = [question.strip() for question in generated.follow_up_questions if question.strip()]
        section_questions.extend(_fallback_questions(section, retrieved))
        for question in section_questions:
            if question not in questions:
                questions.append(question)

    return "\n".join(lines).strip() + "\n", questions
