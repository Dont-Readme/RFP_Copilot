from __future__ import annotations

from pathlib import Path
import re
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings

ASSET_CATEGORIES = (
    "회사소개",
    "제품",
    "실적",
    "인력",
    "특허",
    "재무",
    "레퍼런스",
    "기타",
)


def validate_asset_category(category: str) -> str:
    if category not in ASSET_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported asset category: {category}",
        )
    return category


def sanitize_filename(filename: str) -> str:
    base_name = Path(filename).name.strip() or "upload.bin"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", base_name)


def save_upload_file(file: UploadFile) -> tuple[str, str, str]:
    settings = get_settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)

    display_name = Path(file.filename or "upload.bin").name.strip() or "upload.bin"
    safe_name = sanitize_filename(display_name)
    destination = settings.upload_dir / f"{uuid4().hex}_{safe_name}"
    byte_limit = settings.max_upload_mb * 1024 * 1024
    total_bytes = 0

    try:
        with destination.open("wb") as buffer:
            while chunk := file.file.read(1024 * 1024):
                total_bytes += len(chunk)
                if total_bytes > byte_limit:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Upload exceeded {settings.max_upload_mb}MB limit",
                    )
                buffer.write(chunk)
    except Exception:
        if destination.exists():
            destination.unlink()
        raise
    finally:
        file.file.close()

    relative_path = str(destination.relative_to(settings.app_data_dir))
    return display_name[:255], file.content_type or "application/octet-stream", relative_path
