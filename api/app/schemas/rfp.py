from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RfpFileRole = Literal["notice", "sow", "rfp", "requirements", "other"]


class EvaluationItemPayload(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    weight: float | None = None


class EvaluationItemRead(EvaluationItemPayload):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    created_at: datetime


class RfpRequirementItemPayload(BaseModel):
    requirement_no: str = Field(default="", max_length=100)
    name: str = Field(default="", max_length=255)
    definition: str = ""
    details: str = ""


class RfpRequirementItemRead(RfpRequirementItemPayload):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    sort_order: int
    created_at: datetime


class RfpEvaluationItemPayload(BaseModel):
    item: str = Field(default="", max_length=255)
    score: str = Field(default="", max_length=100)
    notes: str = ""


class RfpEvaluationItemRead(RfpEvaluationItemPayload):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    created_at: datetime


class ProjectFileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    kind: str
    role: RfpFileRole | str
    filename: str
    mime: str
    path: str
    size: int
    created_at: datetime


class RfpExtractionBase(BaseModel):
    status: Literal["draft", "confirmed"] = "draft"
    raw_text: str = ""
    project_summary_text: str = ""
    ocr_required: bool = False


class RfpExtractionUpdate(RfpExtractionBase):
    requirements: list[RfpRequirementItemPayload] = Field(default_factory=list)
    evaluation_items: list[RfpEvaluationItemPayload] = Field(default_factory=list)


class RfpExtractionRead(RfpExtractionBase):
    model_config = ConfigDict(from_attributes=True)

    project_id: int
    updated_at: datetime
    files: list[ProjectFileRead] = Field(default_factory=list)
    requirements: list[RfpRequirementItemRead] = Field(default_factory=list)
    evaluation_items: list[RfpEvaluationItemRead] = Field(default_factory=list)


class RfpFileUploadResponse(BaseModel):
    extraction: RfpExtractionRead
    file: ProjectFileRead
