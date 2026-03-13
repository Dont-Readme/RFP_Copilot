from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.library import LibraryAsset
from app.repositories.chunk_repo import list_chunks_for_document_ids
from app.services.chunking_service import ensure_library_asset_chunks
from app.services.document_text_service import looks_like_binary_text


def build_asset_text_index(db: Session, assets: list[LibraryAsset]) -> dict[int, list[str]]:
    if not assets:
        return {}

    for asset in assets:
        ensure_library_asset_chunks(db, asset)

    chunks = list_chunks_for_document_ids(
        db,
        document_kind="library",
        document_ids=[asset.id for asset in assets],
    )
    text_index: dict[int, list[str]] = {asset.id: [] for asset in assets}
    for chunk in chunks:
        text = (chunk.text_content or "").strip()
        if not text or looks_like_binary_text(text):
            continue
        text_index.setdefault(chunk.document_id, []).append(text)
    return text_index
