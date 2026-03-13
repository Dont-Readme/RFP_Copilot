from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DraftSectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: str
    content_md: str
    status: str
    updated_at: datetime


class DraftSectionUpdate(BaseModel):
    content_md: str = Field(min_length=1)


class OpenQuestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: int
    draft_section_id: int | None
    outline_section_id: int | None
    section_heading_text: str
    question_text: str
    category: str
    severity: str
    source_agent: str
    status: Literal["open", "resolved"]
    created_at: datetime


class OpenQuestionUpdate(BaseModel):
    status: Literal["open", "resolved"]


class RewriteRequest(BaseModel):
    section_id: int
    selected_text: str = Field(min_length=1)
    instruction: str = Field(min_length=1)


class RewriteResponse(BaseModel):
    replacement_text: str
    diff_hint: str | None = None


class DraftChatMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    draft_section_id: int
    role: Literal["user", "assistant"]
    message_text: str
    suggestion_text: str | None
    apply_mode: Literal["replace_selection", "advice_only"]
    selection_start: int | None
    selection_end: int | None
    selection_text: str | None
    applied_at: datetime | None
    created_at: datetime


class DraftChatRequest(BaseModel):
    section_id: int
    message: str = Field(min_length=1)
    selection_start: int | None = None
    selection_end: int | None = None
    selection_text: str | None = None


class DraftChatResponse(BaseModel):
    user_message: DraftChatMessageRead
    assistant_message: DraftChatMessageRead
    review_items: list[OpenQuestionRead] = Field(default_factory=list)


class DraftChatApplyResponse(BaseModel):
    section: DraftSectionRead
    message: DraftChatMessageRead


class DraftSectionPlanRead(BaseModel):
    section_id: int
    heading_text: str
    depth: int
    heading_path: list[str]
    section_goal: str = ""
    assigned_requirement_titles: list[str] = Field(default_factory=list)
    assigned_evaluation_titles: list[str] = Field(default_factory=list)
    assigned_company_facts: list[str] = Field(default_factory=list)
    search_topics: list[str] = Field(default_factory=list)
    status: str = "planned"


class DraftPlanningConfigRead(BaseModel):
    project_id: int
    author_intent: str = ""


class DraftPlanningConfigUpdate(BaseModel):
    author_intent: str = ""


class DraftGenerationUnitRead(BaseModel):
    unit_key: str
    outline_section_id: int
    section_heading_text: str
    unit_title: str
    unit_goal: str = ""
    writing_instruction: str = ""
    writing_mode: str = "execution"
    unit_pattern: str = "functional_workflow"
    required_aspects: list[str] = Field(default_factory=list)
    primary_requirement_titles: list[str] = Field(default_factory=list)
    secondary_requirement_titles: list[str] = Field(default_factory=list)
    asset_titles: list[str] = Field(default_factory=list)
    search_topics: list[str] = Field(default_factory=list)
    outline_fit_warning: str = ""


class DraftRequirementCoverageRead(BaseModel):
    requirement_id: int
    requirement_label: str
    primary_unit_key: str
    primary_outline_section_id: int
    secondary_unit_keys: list[str] = Field(default_factory=list)
    rationale: str = ""


class DraftPlanResponse(BaseModel):
    project_id: int
    ready: bool
    warnings: list[str] = Field(default_factory=list)
    sections: list[DraftSectionPlanRead]
    author_intent: str = ""
    planner_summary: str = ""
    planner_mode: str = "rule_based"
    generation_units: list[DraftGenerationUnitRead] = Field(default_factory=list)
    requirement_coverage: list[DraftRequirementCoverageRead] = Field(default_factory=list)
    coverage_warnings: list[str] = Field(default_factory=list)
    generation_requires_confirmation: bool = False


class DraftGenerateRequest(BaseModel):
    mode: str = Field(default="full")
    confirm_warnings: bool = False


class DraftGenerateResponse(BaseModel):
    section: DraftSectionRead
    questions: list[OpenQuestionRead]


class DraftSearchCitationRead(BaseModel):
    title: str
    url: str
    snippet: str = ""


class DraftSearchSourceRead(BaseModel):
    title: str
    url: str


class DraftSearchTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    outline_section_id: int
    topic: str
    unit_key: str
    purpose: str
    reason: str
    source_stage: str
    expected_output: str
    allowed_domains: list[str] = Field(default_factory=list)
    max_results: int
    query_text: str
    result_summary: str
    citations: list[DraftSearchCitationRead] = Field(default_factory=list)
    sources: list[DraftSearchSourceRead] = Field(default_factory=list)
    status: str
    searched_on: str
    created_at: datetime
    updated_at: datetime
