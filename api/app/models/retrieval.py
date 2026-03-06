from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("document_kind", "document_id", "chunk_index", name="uq_document_chunk"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_kind: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    document_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    project_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    route_label: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    token_estimate: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )
