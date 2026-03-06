from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProjectFile(Base):
    __tablename__ = "project_files"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(50), nullable=False, default="rfp")
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="other")
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )


class RfpExtraction(Base):
    __tablename__ = "rfp_extractions"

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id"), primary_key=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    raw_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    project_summary_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    eligibility_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    submission_docs_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    evaluation_overview_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    format_rules_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    deadline_iso: Mapped[str | None] = mapped_column(String(50), nullable=True)
    contact_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    notes_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    ocr_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class RfpRequirementItem(Base):
    __tablename__ = "rfp_requirement_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    requirement_no: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    definition: Mapped[str] = mapped_column(Text, nullable=False, default="")
    details: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )
