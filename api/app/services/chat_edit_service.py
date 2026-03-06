from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.draft import DraftChatMessage, DraftSection
from app.models.evaluation import EvaluationItem
from app.models.rfp import RfpExtraction, RfpRequirementItem
from app.services.llm_service import LLMConfigurationError, LLMResponseError, LLMService
from app.services.retrieval_service import RetrievedChunk, format_retrieved_context

CHAT_CONTEXT_WINDOW = 900

CHAT_EDIT_SYSTEM_PROMPT = """
You are editing a Korean proposal draft with the user through a chat interface.

Rules:
- Respect the user's edit request exactly.
- Use only information supported by the draft, structured RFP summary, and retrieved evidence.
- If the user selected text, return replacement text only for the selected span, not the full draft.
- If no text is selected, provide guidance only and leave `suggestion_text` empty with `apply_mode=advice_only`.
- Do not invent numbers, certifications, customers, or performance claims.
- If a requested fact is missing, mention that clearly and use `[확인 필요(시스템)]` in the suggestion when needed.
- Keep the assistant reply concise and practical.
""".strip()


class ChatEditError(RuntimeError):
    pass


class StructuredChatEdit(BaseModel):
    assistant_reply: str = ""
    suggestion_text: str = ""
    apply_mode: str = Field(default="advice_only")
    diff_hint: str | None = None


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
        for requirement in requirements[:6]:
            title = requirement.name or requirement.requirement_no or "무제 요구사항"
            detail = requirement.definition or requirement.details
            lines.append(f"  - {title}: {detail[:160] if detail else '세부 내용 확인 필요'}")
    if evaluation_items:
        lines.append("- 주요 평가항목:")
        for item in evaluation_items[:5]:
            score = item.score_text or (f"{item.weight:g}" if item.weight is not None else "")
            suffix = f" ({score})" if score else ""
            note = item.description[:140] if item.description else ""
            lines.append(f"  - {item.title}{suffix}: {note or '비고 없음'}")
    return "\n".join(lines) if lines else "구조화된 RFP 요약 없음"


def _window_around_selection(
    content: str,
    *,
    selection_start: int | None,
    selection_end: int | None,
) -> tuple[str, str]:
    if selection_start is None or selection_end is None or selection_start == selection_end:
        return content[: CHAT_CONTEXT_WINDOW * 2], ""

    before = content[max(0, selection_start - CHAT_CONTEXT_WINDOW) : selection_start]
    selected = content[selection_start:selection_end]
    after = content[selection_end : selection_end + CHAT_CONTEXT_WINDOW]
    excerpt = f"{before}<selected>{selected}</selected>{after}"
    return excerpt, selected


def _format_history(messages: list[DraftChatMessage], limit: int = 8) -> str:
    if not messages:
        return "No prior chat history."

    lines: list[str] = []
    for message in messages[-limit:]:
        prefix = "User" if message.role == "user" else "Assistant"
        lines.append(f"{prefix}: {message.message_text}")
        if message.role == "assistant" and message.suggestion_text:
            lines.append(f"AssistantSuggestion: {message.suggestion_text[:400]}")
    return "\n".join(lines)


def build_chat_edit(
    *,
    llm_service: LLMService,
    project_name: str,
    draft_section: DraftSection,
    extraction: RfpExtraction,
    requirements: list[RfpRequirementItem],
    evaluation_items: list[EvaluationItem],
    user_message: str,
    prior_messages: list[DraftChatMessage],
    retrieved: list[RetrievedChunk],
    selection_start: int | None,
    selection_end: int | None,
) -> StructuredChatEdit:
    excerpt, selected_text = _window_around_selection(
        draft_section.content_md,
        selection_start=selection_start,
        selection_end=selection_end,
    )
    try:
        return llm_service.parse_chat_completion(
            model=llm_service.settings.openai_model_draft,
            system_prompt=CHAT_EDIT_SYSTEM_PROMPT,
            user_prompt=f"""
Project name: {project_name}
Draft title: {draft_section.title}

Structured RFP summary:
{_rfp_summary(extraction, requirements, evaluation_items)}

Recent chat history:
{_format_history(prior_messages)}

Draft excerpt:
{excerpt}

Selected text:
{selected_text or 'No selection'}

Retrieved evidence:
{format_retrieved_context(retrieved, max_items=4)}

User request:
{user_message}

Return:
- `assistant_reply`: what you tell the user
- `suggestion_text`: replacement text for the selected span, or empty if no selection
- `apply_mode`: `replace_selection` or `advice_only`
- `diff_hint`: short note about what changed
""".strip(),
            response_format=StructuredChatEdit,
            max_completion_tokens=1600,
        )
    except (LLMConfigurationError, LLMResponseError) as exc:
        raise ChatEditError(str(exc)) from exc
