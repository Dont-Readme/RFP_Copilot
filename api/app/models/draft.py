from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
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
    outline_section_id: Mapped[int | None] = mapped_column(
        ForeignKey("outline_sections.id"), nullable=True, index=True
    )
    section_heading_text: Mapped[str] = mapped_column(
        String(255), nullable=False, default="", server_default=""
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, default="missing_evidence", server_default="missing_evidence"
    )
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, default="medium", server_default="medium"
    )
    source_agent: Mapped[str] = mapped_column(
        String(20), nullable=False, default="reviewer", server_default="reviewer"
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )


class DraftSectionPlan(Base):
    __tablename__ = "draft_section_plans"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    outline_section_id: Mapped[int] = mapped_column(
        ForeignKey("outline_sections.id"), nullable=False, index=True
    )
    heading_text: Mapped[str] = mapped_column(String(255), nullable=False)
    section_goal: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    assigned_requirement_ids_json: Mapped[str] = mapped_column(
        Text, nullable=False, default="[]", server_default="[]"
    )
    assigned_requirement_text: Mapped[str] = mapped_column(
        Text, nullable=False, default="", server_default=""
    )
    assigned_evaluation_ids_json: Mapped[str] = mapped_column(
        Text, nullable=False, default="[]", server_default="[]"
    )
    assigned_evaluation_text: Mapped[str] = mapped_column(
        Text, nullable=False, default="", server_default=""
    )
    assigned_asset_ids_json: Mapped[str] = mapped_column(
        Text, nullable=False, default="[]", server_default="[]"
    )
    assigned_company_text: Mapped[str] = mapped_column(
        Text, nullable=False, default="", server_default=""
    )
    draft_guidance: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    needs_search: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    search_topics_json: Mapped[str] = mapped_column(
        Text, nullable=False, default="[]", server_default="[]"
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="planned", server_default="planned"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class DraftSearchTask(Base):
    __tablename__ = "draft_search_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    outline_section_id: Mapped[int] = mapped_column(
        ForeignKey("outline_sections.id"), nullable=False, index=True
    )
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    freshness_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    expected_output: Mapped[str] = mapped_column(
        String(100), nullable=False, default="", server_default=""
    )
    query_text: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending", server_default="pending"
    )
    searched_on: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
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
