from __future__ import annotations

from dataclasses import dataclass
import re

from sqlalchemy.orm import Session

from app.models.retrieval import DocumentChunk
from app.repositories.chunk_repo import list_chunks_for_document_ids
from app.repositories.library_repo import list_project_assets
from app.repositories.rfp_repo import list_project_files
from app.services.chunking_service import ensure_library_asset_chunks, ensure_project_file_chunks


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: DocumentChunk
    score: int


def retrieval_tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[A-Za-z0-9가-힣]+", text.lower())
        if len(token) >= 2
    }


def _count_numeric_signals(text: str) -> int:
    return len(re.findall(r"\d+(?:[.,]\d+)?(?:%|건|명|개|억원|만원|개월|년)?", text))


def _build_chunk_label(chunk: DocumentChunk) -> str:
    if chunk.page_start and chunk.page_end:
        if chunk.page_start == chunk.page_end:
            return f"{chunk.title} p.{chunk.page_start}"
        return f"{chunk.title} p.{chunk.page_start}-{chunk.page_end}"
    return chunk.title


def _build_chunk_url(chunk: DocumentChunk) -> str:
    if chunk.page_start:
        return f"local://{chunk.source_path}#page={chunk.page_start}"
    return f"local://{chunk.source_path}"


def _score_chunk(chunk: DocumentChunk, query_tokens: set[str]) -> int:
    haystack = f"{chunk.title} {chunk.route_label or ''} {chunk.text_content}".lower()
    score = sum(4 if token in (chunk.title or "").lower() else 2 for token in query_tokens if token in haystack)
    if chunk.document_kind == "rfp":
        score += 1
    score += min(2, _count_numeric_signals(chunk.text_content))
    return score


def _collect_project_chunks(db: Session, project_id: int) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []

    project_files = list_project_files(db, project_id)
    if project_files:
        for project_file in project_files:
            ensure_project_file_chunks(db, project_file)
        chunks.extend(
            list_chunks_for_document_ids(
                db,
                document_kind="rfp",
                document_ids=[project_file.id for project_file in project_files],
            )
        )

    assets = list_project_assets(db, project_id)
    if assets:
        for asset in assets:
            ensure_library_asset_chunks(db, asset)
        chunks.extend(
            list_chunks_for_document_ids(
                db,
                document_kind="library",
                document_ids=[asset.id for asset in assets],
            )
        )

    return chunks


def retrieve_project_chunks(
    db: Session,
    *,
    project_id: int,
    query: str,
    limit: int = 4,
) -> list[RetrievedChunk]:
    candidate_chunks = _collect_project_chunks(db, project_id)
    if not candidate_chunks:
        return []

    query_tokens = retrieval_tokens(query)
    scored_chunks: list[RetrievedChunk] = []
    for chunk in candidate_chunks:
        score = _score_chunk(chunk, query_tokens) if query_tokens else 0
        scored_chunks.append(RetrievedChunk(chunk=chunk, score=score))

    scored_chunks.sort(
        key=lambda item: (
            -item.score,
            0 if item.chunk.document_kind == "rfp" else 1,
            item.chunk.document_id,
            item.chunk.chunk_index,
        )
    )

    filtered = [item for item in scored_chunks if item.score > 0]
    if filtered:
        return filtered[:limit]
    return scored_chunks[:limit]


def build_citation_payloads_for_query(
    db: Session,
    *,
    project_id: int,
    outline_section_id: int,
    query: str,
    limit: int = 4,
) -> list[dict]:
    retrieved = retrieve_project_chunks(db, project_id=project_id, query=query, limit=limit)
    return build_citation_payloads_from_retrieved(
        outline_section_id=outline_section_id,
        retrieved=retrieved,
    )


def build_citation_payloads_from_retrieved(
    *,
    outline_section_id: int,
    retrieved: list[RetrievedChunk],
) -> list[dict]:
    return [
        {
            "outline_section_id": outline_section_id,
            "source_title": _build_chunk_label(item.chunk),
            "source_url": _build_chunk_url(item.chunk),
            "snippet": item.chunk.text_content[:280],
        }
        for item in retrieved
    ]


def format_retrieved_context(retrieved: list[RetrievedChunk], *, max_items: int = 4) -> str:
    if not retrieved:
        return "관련 문서 근거를 찾지 못했습니다."

    lines: list[str] = []
    for item in retrieved[:max_items]:
        lines.append(f"[{_build_chunk_label(item.chunk)}]")
        lines.append(item.chunk.text_content[:900])
        lines.append("")
    return "\n".join(lines).strip()
