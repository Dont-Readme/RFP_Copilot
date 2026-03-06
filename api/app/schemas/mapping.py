from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.rfp import RfpEvaluationItemRead


class MappingRunRequest(BaseModel):
    strategy: str = Field(default="rules")


class EvalMappingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    evaluation_item_id: int
    draft_section_id: int | None
    section_title: str | None
    strength_score: float
    strength_label: Literal["strong", "weak", "missing"]
    rationale_text: str
    created_at: datetime


class MappingWarningRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    type: Literal["missing", "weak", "overlap"]
    evaluation_item_id: int | None
    draft_section_id: int | None
    message: str
    created_at: datetime


class MappingResultRead(BaseModel):
    strategy: str
    evaluation_items: list[RfpEvaluationItemRead]
    mappings: list[EvalMappingRead]
    warnings: list[MappingWarningRead]
