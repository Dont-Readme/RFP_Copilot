from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EvalMapping(Base):
    __tablename__ = "eval_mappings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    evaluation_item_id: Mapped[int] = mapped_column(
        ForeignKey("evaluation_items.id"), nullable=False, index=True
    )
    draft_section_id: Mapped[int | None] = mapped_column(
        ForeignKey("draft_sections.id"), nullable=True, index=True
    )
    section_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    strength_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    strength_label: Mapped[str] = mapped_column(String(20), nullable=False, default="missing")
    rationale_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )


class MappingWarning(Base):
    __tablename__ = "mapping_warnings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    evaluation_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("evaluation_items.id"), nullable=True, index=True
    )
    draft_section_id: Mapped[int | None] = mapped_column(
        ForeignKey("draft_sections.id"), nullable=True, index=True
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )
