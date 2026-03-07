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


class DraftPlanResponse(BaseModel):
    project_id: int
    ready: bool
    warnings: list[str] = Field(default_factory=list)
    sections: list[DraftSectionPlanRead]


class DraftGenerateRequest(BaseModel):
    mode: str = Field(default="full")


class DraftGenerateResponse(BaseModel):
    section: DraftSectionRead
    questions: list[OpenQuestionRead]
