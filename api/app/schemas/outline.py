from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OutlineSectionWrite(BaseModel):
    id: int | None = None
    parent_id: int | None = None
    sort_order: int | None = Field(default=None, ge=1)
    title: str = Field(min_length=1, max_length=255)
    needs_search: bool = False


class OutlineSaveRequest(BaseModel):
    sections: list[OutlineSectionWrite] = Field(min_length=1)


class OutlineSectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    parent_id: int | None
    sort_order: int
    title: str
    needs_search: bool
    created_at: datetime
    updated_at: datetime


class CitationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    outline_section_id: int
    source_title: str
    source_url: str
    snippet: str
    accessed_at: datetime


class SearchRunRequest(BaseModel):
    section_ids: list[int] = Field(default_factory=list)


class SearchRunResponse(BaseModel):
    project_id: int
    section_ids: list[int]
    citations: list[CitationRead]
