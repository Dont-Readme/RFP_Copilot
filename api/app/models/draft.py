from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DraftSection(Base):
    __tablename__ = "draft_sections"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="기본 초안")
    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="generated")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class OpenQuestion(Base):
    __tablename__ = "open_questions"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    draft_section_id: Mapped[int | None] = mapped_column(
        ForeignKey("draft_sections.id"), nullable=True, index=True
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )


class DraftChatMessage(Base):
    __tablename__ = "draft_chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    draft_section_id: Mapped[int] = mapped_column(
        ForeignKey("draft_sections.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    suggestion_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    apply_mode: Mapped[str] = mapped_column(String(30), nullable=False, default="advice_only")
    selection_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    selection_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    selection_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )
