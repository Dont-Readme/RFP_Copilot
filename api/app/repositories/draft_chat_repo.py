from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.draft import DraftChatMessage, DraftSection


def list_chat_messages(db: Session, project_id: int, draft_section_id: int) -> list[DraftChatMessage]:
    statement = (
        select(DraftChatMessage)
        .where(
            DraftChatMessage.project_id == project_id,
            DraftChatMessage.draft_section_id == draft_section_id,
        )
        .order_by(DraftChatMessage.created_at.asc(), DraftChatMessage.id.asc())
    )
    return list(db.scalars(statement).all())


def create_chat_message(
    db: Session,
    *,
    project_id: int,
    draft_section_id: int,
    role: str,
    message_text: str,
    suggestion_text: str | None = None,
    apply_mode: str = "advice_only",
    selection_start: int | None = None,
    selection_end: int | None = None,
    selection_text: str | None = None,
) -> DraftChatMessage:
    message = DraftChatMessage(
        project_id=project_id,
        draft_section_id=draft_section_id,
        role=role,
        message_text=message_text,
        suggestion_text=suggestion_text,
        apply_mode=apply_mode,
        selection_start=selection_start,
        selection_end=selection_end,
        selection_text=selection_text,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_chat_message(db: Session, project_id: int, message_id: int) -> DraftChatMessage | None:
    statement = select(DraftChatMessage).where(
        DraftChatMessage.project_id == project_id,
        DraftChatMessage.id == message_id,
    )
    return db.scalars(statement).first()


def mark_message_applied(db: Session, message: DraftChatMessage) -> DraftChatMessage:
    message.applied_at = datetime.utcnow()
    db.commit()
    db.refresh(message)
    return message


def apply_message_to_section(
    db: Session,
    *,
    message: DraftChatMessage,
    section: DraftSection,
) -> DraftSection:
    if not message.suggestion_text:
        raise ValueError("Message does not contain an applicable suggestion")
    if message.selection_start is None or message.selection_end is None or message.selection_text is None:
        raise ValueError("Message does not include selection metadata")

    start = message.selection_start
    end = message.selection_end
    if section.content_md[start:end] != message.selection_text:
        fallback_start = section.content_md.find(message.selection_text)
        if fallback_start < 0:
            raise LookupError("Selected text no longer matches the current draft content")
        start = fallback_start
        end = fallback_start + len(message.selection_text)

    section.content_md = (
        section.content_md[:start] + message.suggestion_text + section.content_md[end:]
    )
    section.status = "edited"
    db.commit()
    db.refresh(section)
    return section
