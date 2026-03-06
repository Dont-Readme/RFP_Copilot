from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LibraryAssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_user_id: str
    category: str
    title: str
    filename: str
    mime: str
    path: str
    created_at: datetime


class ProjectAssetLinkPayload(BaseModel):
    asset_ids: list[int] = Field(default_factory=list)


class ProjectAssetLinkResult(BaseModel):
    project_id: int
    asset_ids: list[int]
