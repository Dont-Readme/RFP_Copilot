from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.retrieval import DocumentChunk


def list_document_chunks(
    db: Session, *, document_kind: str, document_id: int
) -> list[DocumentChunk]:
    statement = (
        select(DocumentChunk)
        .where(
            DocumentChunk.document_kind == document_kind,
            DocumentChunk.document_id == document_id,
        )
        .order_by(DocumentChunk.chunk_index.asc(), DocumentChunk.id.asc())
    )
    return list(db.scalars(statement).all())


def list_chunks_for_document_ids(
    db: Session, *, document_kind: str, document_ids: list[int]
) -> list[DocumentChunk]:
    if not document_ids:
        return []

    statement = (
        select(DocumentChunk)
        .where(
            DocumentChunk.document_kind == document_kind,
            DocumentChunk.document_id.in_(document_ids),
        )
        .order_by(DocumentChunk.document_id.asc(), DocumentChunk.chunk_index.asc(), DocumentChunk.id.asc())
    )
    return list(db.scalars(statement).all())


def replace_document_chunks(
    db: Session,
    *,
    document_kind: str,
    document_id: int,
    chunks: list[dict],
) -> list[DocumentChunk]:
    db.execute(
        delete(DocumentChunk).where(
            DocumentChunk.document_kind == document_kind,
            DocumentChunk.document_id == document_id,
        )
    )
    db.add_all(
        [
            DocumentChunk(
                document_kind=document_kind,
                document_id=document_id,
                project_id=chunk.get("project_id"),
                title=chunk["title"],
                source_path=chunk["source_path"],
                chunk_index=chunk["chunk_index"],
                page_start=chunk.get("page_start"),
                page_end=chunk.get("page_end"),
                route_label=chunk.get("route_label"),
                token_estimate=chunk["token_estimate"],
                text_content=chunk["text_content"],
            )
            for chunk in chunks
        ]
    )
    db.commit()
    return list_document_chunks(db, document_kind=document_kind, document_id=document_id)


def delete_document_chunks(db: Session, *, document_kind: str, document_id: int) -> None:
    db.execute(
        delete(DocumentChunk).where(
            DocumentChunk.document_kind == document_kind,
            DocumentChunk.document_id == document_id,
        )
    )
    db.commit()


def delete_project_chunks(db: Session, project_id: int) -> None:
    db.execute(delete(DocumentChunk).where(DocumentChunk.project_id == project_id))
    db.commit()
