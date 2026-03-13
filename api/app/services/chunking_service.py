from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from app.core.config import get_settings
from app.models.library import LibraryAsset
from app.models.rfp import ProjectFile
from app.repositories.chunk_repo import list_document_chunks, replace_document_chunks
from app.services.document_text_service import extract_text_pages_from_path, looks_like_binary_text

MAX_CHUNK_CHARS = 1_400

ROUTE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "overview": ("사업개요", "사업내용", "사업목적", "사업범위", "과업개요", "추진배경", "제안요청개요"),
    "requirements": ("요구사항", "기능요구", "세부요건", "제안요청내용", "과업내용", "요구조건", "요건"),
    "evaluation": ("평가", "배점", "심사", "정량", "정성", "평가항목"),
    "schedule": ("일정", "마감", "마감일", "제안서 접수", "접수기간", "제출기한", "일시"),
}


@dataclass(frozen=True)
class ChunkingResult:
    raw_text: str
    chunks: list[dict]


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _chunks_need_rebuild(chunks: list[dict]) -> bool:
    if not chunks:
        return False
    preview = "\n".join(chunk["text_content"] for chunk in chunks[:3]).strip()
    return looks_like_binary_text(preview)


def _normalize_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n")
    # PDF 목차/리더 라인에서 나오는 장식 점열은 의미 없이 토큰만 늘리므로 제거한다.
    normalized = re.sub(r"(?:[·ㆍ․…]\s*){4,}", " ", normalized)
    normalized = re.sub(r"[^\S\n]{2,}", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def _split_long_block(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    sentences = re.split(r"(?<=[.!?。다])\s+|\n", text)
    parts: list[str] = []
    buffer = ""
    for sentence in sentences:
        candidate = sentence.strip()
        if not candidate:
            continue
        if not buffer:
            buffer = candidate
            continue
        if len(buffer) + 1 + len(candidate) <= max_chars:
            buffer = f"{buffer} {candidate}"
            continue
        parts.append(buffer)
        buffer = candidate

    if buffer:
        parts.append(buffer)

    if not parts:
        return [text[:max_chars], text[max_chars:]]
    return parts


def _split_blocks(text: str, max_chars: int) -> list[str]:
    normalized = _normalize_text(text)
    if not normalized:
        return []

    blocks = [block.strip() for block in re.split(r"\n\s*\n+", normalized) if block.strip()]
    if not blocks:
        blocks = [normalized]

    chunks: list[str] = []
    for block in blocks:
        chunks.extend(_split_long_block(block, max_chars))
    return chunks


def _detect_route_label(text: str) -> str:
    lowered = text.lower()
    best_label = "general"
    best_score = 0
    for label, keywords in ROUTE_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword.lower() in lowered)
        if score > best_score:
            best_label = label
            best_score = score
    return best_label


def build_document_chunks(
    *,
    document_kind: str,
    document_id: int,
    project_id: int | None,
    title: str,
    source_path: str,
    absolute_path: Path,
    max_chunk_chars: int = MAX_CHUNK_CHARS,
) -> ChunkingResult:
    pages = extract_text_pages_from_path(absolute_path)
    chunks: list[dict] = []
    raw_parts: list[str] = []
    chunk_index = 1

    for page_number, page_text in pages:
        normalized_page = _normalize_text(page_text)
        if not normalized_page:
            continue
        raw_parts.append(normalized_page)
        for block in _split_blocks(normalized_page, max_chunk_chars):
            chunks.append(
                {
                    "document_kind": document_kind,
                    "document_id": document_id,
                    "project_id": project_id,
                    "title": title,
                    "source_path": source_path,
                    "chunk_index": chunk_index,
                    "page_start": page_number,
                    "page_end": page_number,
                    "route_label": _detect_route_label(block),
                    "token_estimate": _estimate_tokens(block),
                    "text_content": block,
                }
            )
            chunk_index += 1

    return ChunkingResult(raw_text="\n\n".join(raw_parts).strip(), chunks=chunks)


def ensure_project_file_chunks(db, project_file: ProjectFile) -> ChunkingResult:
    existing_chunks = list_document_chunks(
        db,
        document_kind="rfp",
        document_id=project_file.id,
    )
    if existing_chunks:
        cached = ChunkingResult(
            raw_text="\n\n".join(chunk.text_content for chunk in existing_chunks).strip(),
            chunks=[
                {
                    "document_kind": chunk.document_kind,
                    "document_id": chunk.document_id,
                    "project_id": chunk.project_id,
                    "title": chunk.title,
                    "source_path": chunk.source_path,
                    "chunk_index": chunk.chunk_index,
                    "page_start": chunk.page_start,
                    "page_end": chunk.page_end,
                    "route_label": chunk.route_label,
                    "token_estimate": chunk.token_estimate,
                    "text_content": chunk.text_content,
                }
                for chunk in existing_chunks
            ],
        )
        if not _chunks_need_rebuild(cached.chunks):
            return cached

    settings = get_settings()
    result = build_document_chunks(
        document_kind="rfp",
        document_id=project_file.id,
        project_id=project_file.project_id,
        title=project_file.filename,
        source_path=project_file.path,
        absolute_path=settings.app_data_dir / project_file.path,
    )
    replace_document_chunks(
        db,
        document_kind="rfp",
        document_id=project_file.id,
        chunks=result.chunks,
    )
    return result


def rebuild_project_file_chunks(db, project_file: ProjectFile) -> ChunkingResult:
    settings = get_settings()
    result = build_document_chunks(
        document_kind="rfp",
        document_id=project_file.id,
        project_id=project_file.project_id,
        title=project_file.filename,
        source_path=project_file.path,
        absolute_path=settings.app_data_dir / project_file.path,
    )
    replace_document_chunks(
        db,
        document_kind="rfp",
        document_id=project_file.id,
        chunks=result.chunks,
    )
    return result


def ensure_library_asset_chunks(db, asset: LibraryAsset) -> ChunkingResult:
    existing_chunks = list_document_chunks(
        db,
        document_kind="library",
        document_id=asset.id,
    )
    if existing_chunks:
        cached = ChunkingResult(
            raw_text="\n\n".join(chunk.text_content for chunk in existing_chunks).strip(),
            chunks=[
                {
                    "document_kind": chunk.document_kind,
                    "document_id": chunk.document_id,
                    "project_id": chunk.project_id,
                    "title": chunk.title,
                    "source_path": chunk.source_path,
                    "chunk_index": chunk.chunk_index,
                    "page_start": chunk.page_start,
                    "page_end": chunk.page_end,
                    "route_label": chunk.route_label,
                    "token_estimate": chunk.token_estimate,
                    "text_content": chunk.text_content,
                }
                for chunk in existing_chunks
            ],
        )
        if not _chunks_need_rebuild(cached.chunks):
            return cached

    settings = get_settings()
    result = build_document_chunks(
        document_kind="library",
        document_id=asset.id,
        project_id=None,
        title=asset.title,
        source_path=asset.path,
        absolute_path=settings.app_data_dir / asset.path,
    )
    replace_document_chunks(
        db,
        document_kind="library",
        document_id=asset.id,
        chunks=result.chunks,
    )
    return result
