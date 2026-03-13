from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DebugDocumentChunkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chunk_index: int
    page_start: int | None = None
    page_end: int | None = None
    route_label: str | None = None
    token_estimate: int
    text_content: str
    created_at: datetime


class DebugRfpFileChunksRead(BaseModel):
    file_id: int
    filename: str
    role: str
    mime: str
    size: int
    raw_text: str
    chunk_count: int
    chunks: list[DebugDocumentChunkRead] = Field(default_factory=list)


class DebugRfpChunksResponse(BaseModel):
    project_id: int
    files: list[DebugRfpFileChunksRead] = Field(default_factory=list)


class PromptTraceRead(BaseModel):
    id: str
    project_id: int
    trace_kind: str
    model: str
    system_prompt: str | None = None
    user_prompt: str | None = None
    input_text: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class PromptTraceListResponse(BaseModel):
    project_id: int
    traces: list[PromptTraceRead] = Field(default_factory=list)


class DebugPlannerRequirementCandidateRead(BaseModel):
    requirement_id: int
    requirement_no: str
    name: str
    definition: str
    details: str
    score: int
    matched_tokens: list[str] = Field(default_factory=list)
    selected: bool


class DebugPlannerEvaluationCandidateRead(BaseModel):
    evaluation_item_id: int
    item: str
    score_text: str
    notes: str
    score: int
    matched_tokens: list[str] = Field(default_factory=list)
    selected: bool


class DebugPlannerAssetCandidateRead(BaseModel):
    asset_id: int
    category: str
    title: str
    score: int
    matched_tokens: list[str] = Field(default_factory=list)
    compact_heading_match: bool
    selected: bool
    snippet_previews: list[str] = Field(default_factory=list)


class DebugPlannerSearchTaskRead(BaseModel):
    topic: str
    reason: str
    freshness_required: bool = True
    expected_output: str = ""


class DebugPlannerSectionRead(BaseModel):
    section_id: int
    heading_text: str
    heading_path: list[str] = Field(default_factory=list)
    section_tokens: list[str] = Field(default_factory=list)
    section_goal: str
    draft_guidance: str = ""
    assigned_company_facts: list[str] = Field(default_factory=list)
    search_tasks: list[DebugPlannerSearchTaskRead] = Field(default_factory=list)
    requirement_candidates: list[DebugPlannerRequirementCandidateRead] = Field(default_factory=list)
    evaluation_candidates: list[DebugPlannerEvaluationCandidateRead] = Field(default_factory=list)
    asset_candidates: list[DebugPlannerAssetCandidateRead] = Field(default_factory=list)


class DebugPlannerResponse(BaseModel):
    project_id: int
    ready: bool
    warnings: list[str] = Field(default_factory=list)
    sections: list[DebugPlannerSectionRead] = Field(default_factory=list)
