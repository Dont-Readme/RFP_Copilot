from __future__ import annotations

from app.services.prompts.draft import (
    CHAT_EDIT_SYSTEM_PROMPT,
    DRAFT_ADAPTIVE_RESEARCH_SYSTEM_PROMPT,
    DRAFT_UNIT_DESIGN_SYSTEM_PROMPT,
    DRAFT_SECTION_SYSTEM_PROMPT,
    build_draft_adaptive_research_user_prompt,
    build_chat_edit_user_prompt,
    build_draft_unit_design_user_prompt,
    build_draft_section_user_prompt,
)
from app.services.prompts.planner import (
    DRAFT_PLANNER_BATCH_SYSTEM_PROMPT,
    DRAFT_PLANNER_OVERVIEW_SYSTEM_PROMPT,
    build_draft_planner_batch_prompt,
    build_draft_planner_overview_prompt,
)
from app.services.prompts.rfp import (
    EVALUATION_SYSTEM_PROMPT,
    EVALUATION_USER_PROMPT_TEMPLATE,
    PROJECT_SUMMARY_SYSTEM_PROMPT,
    PROJECT_SUMMARY_USER_PROMPT_TEMPLATE,
    REQUIREMENTS_SYSTEM_PROMPT,
    REQUIREMENTS_USER_PROMPT_TEMPLATE,
    build_evaluation_user_prompt,
    build_project_summary_user_prompt,
    build_requirements_user_prompt,
)
from app.services.prompts.search import build_research_request_prompt, build_web_search_prompt

__all__ = [
    "CHAT_EDIT_SYSTEM_PROMPT",
    "DRAFT_ADAPTIVE_RESEARCH_SYSTEM_PROMPT",
    "DRAFT_UNIT_DESIGN_SYSTEM_PROMPT",
    "DRAFT_SECTION_SYSTEM_PROMPT",
    "EVALUATION_SYSTEM_PROMPT",
    "EVALUATION_USER_PROMPT_TEMPLATE",
    "PROJECT_SUMMARY_SYSTEM_PROMPT",
    "PROJECT_SUMMARY_USER_PROMPT_TEMPLATE",
    "REQUIREMENTS_SYSTEM_PROMPT",
    "REQUIREMENTS_USER_PROMPT_TEMPLATE",
    "build_draft_adaptive_research_user_prompt",
    "build_chat_edit_user_prompt",
    "build_draft_planner_batch_prompt",
    "build_draft_planner_overview_prompt",
    "build_draft_unit_design_user_prompt",
    "build_draft_section_user_prompt",
    "build_evaluation_user_prompt",
    "build_project_summary_user_prompt",
    "build_requirements_user_prompt",
    "build_research_request_prompt",
    "build_web_search_prompt",
    "DRAFT_PLANNER_BATCH_SYSTEM_PROMPT",
    "DRAFT_PLANNER_OVERVIEW_SYSTEM_PROMPT",
]
