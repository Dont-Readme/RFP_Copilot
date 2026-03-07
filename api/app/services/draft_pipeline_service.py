from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.evaluation import EvaluationItem
from app.models.library import LibraryAsset
from app.models.outline import OutlineSection
from app.models.project import Project
from app.models.rfp import RfpExtraction, RfpRequirementItem
from app.repositories.draft_repo import (
    list_search_tasks,
    replace_section_plans,
    update_search_task,
    update_section_plan_status,
)
from app.repositories.outline_repo import replace_citations_for_sections
from app.services.draft_plan_service import DraftPlanResult, build_draft_plan
from app.services.draft_service import generate_section_draft
from app.services.fresh_search_service import FreshSearchError, build_fresh_search_query, run_fresh_search
from app.services.llm_service import LLMService
from app.services.review_item_service import (
    ReviewItemPayload,
    build_heading_text,
    build_review_items_for_section,
    infer_fallback_review_items,
    merge_review_payloads,
)
from app.services.section_review_service import SectionReviewError, review_section


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
                        "reason": task.reason,
                        "freshness_required": task.freshness_required,
                        "expected_output": task.expected_output,
                        "status": "pending",
                    }
                    for task in section_plan.search_tasks
                ],
                "status": section_plan.status,
            }
        )
    return snapshots


def _research_section(
    *,
    db: Session,
    project_id: int,
    outline_section_id: int,
    heading_text: str,
) -> tuple[list[str], list[dict], list[ReviewItemPayload]]:
    search_context: list[str] = []
    citations: list[dict] = []
    review_items: list[ReviewItemPayload] = []
    tasks = list_search_tasks(db, project_id=project_id, outline_section_id=outline_section_id)
    if not tasks:
        replace_citations_for_sections(
            db,
            project_id=project_id,
            section_ids=[outline_section_id],
            citations=[],
        )
        return search_context, citations, review_items

    update_section_plan_status(
        db,
        project_id=project_id,
        outline_section_id=outline_section_id,
        status="search_pending",
    )

    for task in tasks:
        query_text, searched_on = build_fresh_search_query(task.topic)
        update_search_task(
            db,
            task=task,
            status="running",
            query_text=query_text,
            searched_on=searched_on,
        )
        try:
            results = run_fresh_search(topic=task.topic)
            update_search_task(
                db,
                task=task,
                status="completed",
                query_text=query_text,
                searched_on=searched_on,
            )
        except FreshSearchError:
            update_search_task(
                db,
                task=task,
                status="failed",
                query_text=query_text,
                searched_on=searched_on,
            )
            review_items.append(
                ReviewItemPayload(
                    outline_section_id=outline_section_id,
                    section_heading_text=heading_text,
                    question_text=f"`{task.topic}` 최신 검색을 확인하지 못했습니다. 수동 확인이 필요합니다.",
                    category="needs_fresh_search",
                    severity="medium",
                    source_agent="researcher",
                )
            )
            continue

        for result in results:
            search_context.append(f"{result.source_title} ({result.searched_on}): {result.snippet}")
            citations.append(
                {
                    "outline_section_id": outline_section_id,
                    "source_title": result.source_title,
                    "source_url": result.source_url,
                    "snippet": f"[{result.searched_on}] {result.snippet}",
                }
            )

    replace_citations_for_sections(
        db,
        project_id=project_id,
        section_ids=[outline_section_id],
        citations=citations,
    )
    update_section_plan_status(
        db,
        project_id=project_id,
        outline_section_id=outline_section_id,
        status="research_complete",
    )
    return search_context, citations, review_items


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
) -> tuple[str, list[ReviewItemPayload], DraftPlanResult]:
    plan_result = build_draft_plan(
        project_name=project.name,
        sections=sections,
        extraction=extraction,
        requirements=requirements,
        evaluation_items=evaluation_items,
        assets=assets,
    )
    replace_section_plans(
        db,
        project_id=project.id,
        plans=_plan_snapshots(plan_result),
    )

    lines = [project.name]
    collected_review_items: list[ReviewItemPayload] = []

    for section_plan in plan_result.sections:
        heading_text = build_heading_text(section_plan.section)
        update_section_plan_status(
            db,
            project_id=project.id,
            outline_section_id=section_plan.section.id,
            status="drafting",
        )

        search_context, _, research_review_items = _research_section(
            db=db,
            project_id=project.id,
            outline_section_id=section_plan.section.id,
            heading_text=heading_text,
        )
        collected_review_items.extend(research_review_items)

        generated = generate_section_draft(
            llm_service=llm_service,
            project_name=project.name,
            section=section_plan.section,
            extraction=extraction,
            section_goal=section_plan.section_goal,
            draft_guidance=section_plan.draft_guidance,
            requirements=section_plan.assigned_requirements,
            evaluation_items=section_plan.assigned_evaluation_items,
            company_facts=section_plan.assigned_company_facts,
            search_context=search_context,
        )

        lines.extend(["", heading_text])
        if generated.content_md:
            lines.append(generated.content_md)

        writer_review_items = build_review_items_for_section(
            outline_section_id=section_plan.section.id,
            section_heading_text=heading_text,
            item_texts=generated.system_review_items,
            category="missing_evidence",
            severity="medium",
            source_agent="writer",
        )
        try:
            reviewer_items = review_section(
                llm_service=llm_service,
                section=section_plan.section,
                section_goal=section_plan.section_goal,
                draft_guidance=section_plan.draft_guidance,
                content_md=generated.content_md,
                requirements=section_plan.assigned_requirements,
                evaluation_items=section_plan.assigned_evaluation_items,
                search_snippets=search_context,
            )
        except SectionReviewError:
            reviewer_items = [
                ReviewItemPayload(
                    outline_section_id=section_plan.section.id,
                    section_heading_text=heading_text,
                    question_text="자동 검토에 실패했습니다. 이 섹션은 수동 확인이 필요합니다.",
                    category="missing_evidence",
                    severity="medium",
                    source_agent="reviewer",
                )
            ]

        fallback_items = build_review_items_for_section(
            outline_section_id=section_plan.section.id,
            section_heading_text=heading_text,
            item_texts=infer_fallback_review_items(
                section_heading_text=heading_text,
                summary_text=extraction.project_summary_text,
            ),
            category="missing_evidence",
            severity="medium",
            source_agent="system",
        )

        section_review_items = merge_review_payloads(
            writer_review_items,
            reviewer_items,
            fallback_items,
        )
        if not generated.content_md and not section_review_items:
            section_review_items = [
                ReviewItemPayload(
                    outline_section_id=section_plan.section.id,
                    section_heading_text=heading_text,
                    question_text="초안 생성 결과가 비어 있습니다.",
                    category="unclear_scope",
                    severity="high",
                    source_agent="writer",
                )
            ]

        collected_review_items.extend(section_review_items)
        update_section_plan_status(
            db,
            project_id=project.id,
            outline_section_id=section_plan.section.id,
            status="done",
        )

    return "\n".join(lines).strip() + "\n", merge_review_payloads(collected_review_items), plan_result
