from __future__ import annotations

from collections import defaultdict
import re

from sqlalchemy.orm import Session

from app.models.evaluation import EvaluationItem
from app.models.library import LibraryAsset
from app.models.outline import OutlineSection
from app.models.project import Project
from app.models.rfp import RfpExtraction, RfpRequirementItem
from app.repositories.draft_repo import (
    replace_section_plans,
    update_section_plan_status,
)
from app.repositories.outline_repo import replace_citations_for_sections
from app.services.asset_context_service import build_asset_text_index
from app.services.draft_generation_taxonomy import (
    default_required_aspects_for_pattern,
    infer_unit_pattern,
)
from app.services.draft_plan_service import (
    DraftGenerationUnit,
    DraftPlanResult,
)
from app.services.draft_planner_v2_service import build_ai_draft_plan
from app.services.draft_service import generate_section_draft
from app.services.llm_service import LLMService
from app.services.research_service import ResearchResult
from app.services.review_item_service import build_heading_text


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text).strip().lower()


def _plan_snapshots(plan: DraftPlanResult) -> list[dict]:
    snapshots: list[dict] = []
    for section_plan in plan.sections:
        snapshots.append(
            {
                "outline_section_id": section_plan.section.id,
                "heading_text": section_plan.heading_text,
                "section_goal": section_plan.section_goal,
                "assigned_requirement_ids": [item.id for item in section_plan.assigned_requirements],
                "assigned_requirement_text": "\n".join(
                    f"- {(item.name or item.requirement_no or '요구사항').strip()}: {(item.definition or item.details or '').strip()}"
                    for item in section_plan.assigned_requirements
                ),
                "assigned_evaluation_ids": [item.id for item in section_plan.assigned_evaluation_items],
                "assigned_evaluation_text": "\n".join(
                    f"- {(item.item or '평가항목').strip()}: {(item.notes or item.score or '').strip()}"
                    for item in section_plan.assigned_evaluation_items
                ),
                "assigned_asset_ids": [item.id for item in section_plan.assigned_assets],
                "assigned_company_text": "\n".join(section_plan.assigned_company_facts),
                "draft_guidance": section_plan.draft_guidance,
                "needs_search": bool(section_plan.search_tasks),
                "search_topics": [task.topic for task in section_plan.search_tasks],
                "search_tasks": [
                    {
                        "topic": task.topic,
                        "purpose": task.purpose,
                        "reason": task.reason,
                        "freshness_required": task.freshness_required,
                        "expected_output": task.expected_output,
                        "allowed_domains": task.allowed_domains,
                        "max_results": task.max_results,
                        "source_stage": "planned",
                        "status": "pending",
                    }
                    for task in section_plan.search_tasks
                ],
                "status": section_plan.status,
            }
        )
    return snapshots


def _citations_from_research_results(
    *,
    outline_section_id: int,
    results: list[ResearchResult],
) -> list[dict]:
    citations: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for result in results:
        for citation in result.citations:
            key = (citation.url, citation.snippet)
            if key in seen:
                continue
            seen.add(key)
            citations.append(
                {
                    "outline_section_id": outline_section_id,
                    "source_title": citation.title,
                    "source_url": citation.url,
                    "snippet": f"[{result.searched_on}] {citation.snippet}",
                }
            )
    return citations


def _default_unit(section: OutlineSection, section_goal: str, draft_guidance: str) -> DraftGenerationUnit:
    heading_text = build_heading_text(section)
    compact_heading = _compact(heading_text)
    if any(keyword in compact_heading for keyword in ("배경", "현황", "환경", "시장")):
        writing_mode = "background"
    elif any(keyword in compact_heading for keyword in ("필요", "목적", "기대효과")):
        writing_mode = "need"
    elif any(keyword in compact_heading for keyword in ("전략", "추진", "방법론", "체계")):
        writing_mode = "strategy"
    elif any(keyword in compact_heading for keyword in ("운영", "품질", "보안", "유지보수")):
        writing_mode = "operations"
    elif any(keyword in compact_heading for keyword in ("회사", "실적", "특허", "역량", "소개")):
        writing_mode = "evidence"
    else:
        writing_mode = "execution"
    unit_pattern = infer_unit_pattern(
        writing_mode=writing_mode,
        heading_text=heading_text,
        requirements=[],
    )
    return DraftGenerationUnit(
        unit_key=f"section-{section.id}-default",
        outline_section_id=section.id,
        unit_title=heading_text,
        section_heading_text=heading_text,
        section_goal=section_goal,
        unit_goal=section_goal,
        writing_instruction=draft_guidance,
        writing_mode=writing_mode,
        unit_pattern=unit_pattern,
        required_aspects=default_required_aspects_for_pattern(unit_pattern),
    )


def run_draft_pipeline(
    *,
    db: Session,
    project: Project,
    sections: list[OutlineSection],
    extraction: RfpExtraction,
    requirements: list[RfpRequirementItem],
    evaluation_items: list[EvaluationItem],
    assets: list[LibraryAsset],
    llm_service: LLMService,
    asset_text_index: dict[int, list[str]] | None = None,
    plan_result: DraftPlanResult | None = None,
) -> tuple[str, list[object], DraftPlanResult]:
    effective_asset_text_index = (
        asset_text_index if asset_text_index is not None else build_asset_text_index(db, assets)
    )
    effective_plan_result = plan_result or build_ai_draft_plan(
        llm_service=llm_service,
        project_id=project.id,
        project_name=project.name,
        author_intent="",
        sections=sections,
        extraction=extraction,
        requirements=requirements,
        evaluation_items=evaluation_items,
        assets=assets,
        asset_text_index=effective_asset_text_index,
    )
    replace_section_plans(
        db,
        project_id=project.id,
        plans=_plan_snapshots(effective_plan_result),
    )

    requirement_by_id = {item.id: item for item in requirements}
    evaluation_by_id = {item.id: item for item in evaluation_items}
    units_by_section: dict[int, list[DraftGenerationUnit]] = defaultdict(list)
    for unit in effective_plan_result.generation_units:
        units_by_section[unit.outline_section_id].append(unit)

    lines = [project.name]
    for section_plan in effective_plan_result.sections:
        section = section_plan.section
        heading_text = build_heading_text(section)
        update_section_plan_status(
            db,
            project_id=project.id,
            outline_section_id=section.id,
            status="drafting",
        )

        section_units = units_by_section.get(section.id) or [
            _default_unit(section, section_plan.section_goal, section_plan.draft_guidance)
        ]
        section_citations: list[dict] = []

        lines.extend(["", heading_text])

        for unit in section_units:
            render_subheading = (
                len(section_units) > 1 or _compact(unit.unit_title) != _compact(heading_text)
            )
            section_heading_text = (
                f"{heading_text} / {unit.unit_title}" if render_subheading else heading_text
            )

            generated = generate_section_draft(
                db=db,
                llm_service=llm_service,
                project_id=project.id,
                project_name=project.name,
                section=section,
                unit_key=unit.unit_key,
                extraction=extraction,
                section_goal=unit.section_goal,
                unit_title=unit.unit_title,
                unit_goal=unit.unit_goal,
                draft_guidance=unit.writing_instruction,
                writing_mode=unit.writing_mode,
                unit_pattern=unit.unit_pattern,
                required_aspects=unit.required_aspects,
                requirements=[
                    requirement_by_id[requirement_id]
                    for requirement_id in unit.primary_requirement_ids + unit.secondary_requirement_ids
                    if requirement_id in requirement_by_id
                ],
                evaluation_items=[
                    evaluation_by_id[evaluation_id]
                    for evaluation_id in unit.evaluation_item_ids
                    if evaluation_id in evaluation_by_id
                ],
                company_facts=unit.company_facts or section_plan.assigned_company_facts,
                search_tasks=unit.search_tasks,
            )
            section_citations.extend(
                _citations_from_research_results(
                    outline_section_id=section.id,
                    results=generated.research_results,
                )
            )

            if render_subheading:
                lines.extend(["", f"#### {unit.unit_title}"])
            if generated.content_md:
                lines.append(generated.content_md)

        replace_citations_for_sections(
            db,
            project_id=project.id,
            section_ids=[section.id],
            citations=section_citations,
        )
        update_section_plan_status(
            db,
            project_id=project.id,
            outline_section_id=section.id,
            status="done",
        )

    return "\n".join(lines).strip() + "\n", [], effective_plan_result
