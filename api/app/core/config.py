from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path

from dotenv import load_dotenv

API_DIR = Path(__file__).resolve().parents[2]
load_dotenv(API_DIR / ".env", override=False)


def _resolve_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (API_DIR / path).resolve()


def _normalize_database_url(value: str) -> str:
    sqlite_prefix = "sqlite:///"
    if not value.startswith(sqlite_prefix):
        return value

    raw_path = value[len(sqlite_prefix) :]
    if raw_path.startswith("/"):
        return value

    return f"{sqlite_prefix}{_resolve_path(raw_path)}"


def _read_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str
    database_url: str
    app_data_dir: Path
    upload_dir: Path
    export_dir: Path
    max_upload_mb: int
    openai_api_key: str
    openai_base_url: str
    openai_timeout_seconds: float
    openai_model_extraction: str
    openai_model_draft: str
    openai_model_research: str
    ocr_enabled: bool


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "RFP Copilot API"),
        database_url=_normalize_database_url(
            os.getenv("DATABASE_URL", "sqlite:///../data/app.db")
        ),
        app_data_dir=_resolve_path(os.getenv("APP_DATA_DIR", "../data")),
        upload_dir=_resolve_path(os.getenv("UPLOAD_DIR", "../data/uploads")),
        export_dir=_resolve_path(os.getenv("EXPORT_DIR", "../data/exports")),
        max_upload_mb=int(os.getenv("MAX_UPLOAD_MB", "50")),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        openai_timeout_seconds=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "120")),
        openai_model_extraction=os.getenv("OPENAI_MODEL_EXTRACTION", "gpt-4.1-mini"),
        openai_model_draft=os.getenv("OPENAI_MODEL_DRAFT", "gpt-4.1-mini"),
        openai_model_research=os.getenv("OPENAI_MODEL_RESEARCH", "gpt-5-mini"),
        ocr_enabled=_read_bool("OCR_ENABLED", True),
    )
