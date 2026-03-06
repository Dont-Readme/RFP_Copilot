from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ExportCreateRequest(BaseModel):
    formats: list[Literal["md", "txt", "docx", "xlsx"]] = Field(default_factory=lambda: ["md"])


class ExportSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: int
    preview_md_path: str
    files_json: str
    status: str
    created_at: datetime


class ExportPreviewRead(BaseModel):
    export_session_id: str
    preview_md: str
    formats: list[str]
