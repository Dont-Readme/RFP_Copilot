from __future__ import annotations

from pydantic import BaseModel, Field


class ResearchRequestItem(BaseModel):
    query: str = Field(min_length=1)
    purpose: str = ""
    reason: str = ""
    expected_output: str = ""
    allowed_domains: list[str] = Field(default_factory=list)
    max_results: int = Field(default=4, ge=1, le=8)
    external_web_access: bool = True
    source_stage: str = "manual"
    context_summary: str = ""


class ResearchRunRequest(BaseModel):
    section_heading: str = ""
    writing_mode: str = ""
    unit_pattern: str = ""
    goal: str = ""
    requirements_summary: str = ""
    search_requests: list[ResearchRequestItem] = Field(default_factory=list)


class ResearchCitationRead(BaseModel):
    title: str
    url: str
    snippet: str


class ResearchSourceRead(BaseModel):
    title: str
    url: str


class ResearchResultRead(BaseModel):
    query: str
    purpose: str = ""
    reason: str = ""
    expected_output: str = ""
    searched_on: str
    summary: str
    citations: list[ResearchCitationRead] = Field(default_factory=list)
    sources: list[ResearchSourceRead] = Field(default_factory=list)
    source_stage: str = "manual"


class ResearchRunResponse(BaseModel):
    project_id: int
    section_heading: str = ""
    writing_mode: str = ""
    unit_pattern: str = ""
    results: list[ResearchResultRead] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
