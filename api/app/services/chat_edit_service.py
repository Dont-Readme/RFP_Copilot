from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.draft import DraftChatMessage, DraftSection
from app.models.evaluation import EvaluationItem
from app.models.rfp import RfpExtraction, RfpRequirementItem
from app.services.llm_service import LLMConfigurationError, LLMResponseError, LLMService
from app.services.prompts import (
    CHAT_EDIT_SYSTEM_PROMPT,
    build_chat_edit_user_prompt,
)
from app.services.review_item_service import strip_inline_review_items

CHAT_CONTEXT_WINDOW = 900


class ChatEditError(RuntimeError):
    pass


class StructuredChatEdit(BaseModel):
    assistant_reply: str = ""
    suggestion_text: str = ""
    apply_mode: str = Field(default="advice_only")
    diff_hint: str | None = None
    system_review_items: list[str] = Field(default_factory=list)


def _rfp_summary(
    extraction: RfpExtraction,
    requirements: list[RfpRequirementItem],
    evaluation_items: list[EvaluationItem],
) -> str:
    lines = []
    if extraction.project_summary_text:
        lines.append("- 구조화된 사업 개요:")
        lines.append(extraction.project_summary_text)
    if requirements:
        lines.append("- 주요 요구사항:")
        for requirement in requirements[:6]:
            title = requirement.name or requirement.requirement_no or "무제 요구사항"
            detail = requirement.definition or requirement.details
            lines.append(f"  - {title}: {detail[:160] if detail else '세부 내용 확인 필요'}")
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
    project_id: int,
    project_name: str,
    draft_section: DraftSection,
    extraction: RfpExtraction,
    requirements: list[RfpRequirementItem],
    evaluation_items: list[EvaluationItem],
    user_message: str,
    prior_messages: list[DraftChatMessage],
    selection_start: int | None,
    selection_end: int | None,
) -> StructuredChatEdit:
    excerpt, selected_text = _window_around_selection(
        draft_section.content_md,
        selection_start=selection_start,
        selection_end=selection_end,
    )
    try:
        generated = llm_service.parse_chat_completion(
            model=llm_service.settings.openai_model_draft,
            system_prompt=CHAT_EDIT_SYSTEM_PROMPT,
            user_prompt=build_chat_edit_user_prompt(
                project_name=project_name,
                draft_title=draft_section.title,
                rfp_summary=_rfp_summary(extraction, requirements, evaluation_items),
                recent_chat_history=_format_history(prior_messages),
                draft_excerpt=excerpt,
                selected_text=selected_text or "No selection",
                user_request=user_message,
            ),
            response_format=StructuredChatEdit,
            max_completion_tokens=1600,
            trace_project_id=project_id,
            trace_kind="draft.chat",
            trace_metadata={
                "draft_section_id": draft_section.id,
                "draft_title": draft_section.title,
                "selection_start": selection_start,
                "selection_end": selection_end,
                "has_selection": bool(selected_text),
                "prior_message_count": len(prior_messages),
            },
        )
    except (LLMConfigurationError, LLMResponseError) as exc:
        raise ChatEditError(str(exc)) from exc

    assistant_reply, _assistant_review_items = strip_inline_review_items(generated.assistant_reply.strip())
    suggestion_text, _suggestion_review_items = strip_inline_review_items(generated.suggestion_text.strip())

    return StructuredChatEdit(
        assistant_reply=assistant_reply or "수정 제안을 준비했습니다.",
        suggestion_text=suggestion_text,
        apply_mode=generated.apply_mode,
        diff_hint=generated.diff_hint,
        system_review_items=[],
    )
