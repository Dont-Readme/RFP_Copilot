from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.evaluation_repo import list_evaluation_items
from app.repositories.library_repo import list_project_assets
from app.repositories.outline_repo import ensure_project_outline
from app.repositories.chunk_repo import list_document_chunks
from app.repositories.project_repo import get_project
from app.repositories.rfp_repo import ensure_rfp_extraction, list_project_files, list_requirement_items
from app.schemas.debug import (
    DebugPlannerResponse,
    DebugPlannerSectionRead,
    DebugPlannerSearchTaskRead,
    DebugPlannerAssetCandidateRead,
    DebugPlannerEvaluationCandidateRead,
    DebugPlannerRequirementCandidateRead,
    DebugRfpChunksResponse,
    DebugRfpFileChunksRead,
    PromptTraceListResponse,
    PromptTraceRead,
)
from app.services.asset_context_service import build_asset_text_index
from app.services.chunking_service import ensure_project_file_chunks, rebuild_project_file_chunks
from app.services.draft_plan_service import build_draft_plan_debug
from app.services.prompt_trace_service import list_prompt_traces

router = APIRouter(tags=["debug"])


def _build_rfp_chunks_response(db: Session, project_id: int) -> DebugRfpChunksResponse:
    files = list_project_files(db, project_id)
    return DebugRfpChunksResponse(
        project_id=project_id,
        files=[
            DebugRfpFileChunksRead(
                file_id=project_file.id,
                filename=project_file.filename,
                role=project_file.role,
                mime=project_file.mime,
                size=project_file.size,
                raw_text=ensure_project_file_chunks(db, project_file).raw_text,
                chunk_count=len(list_document_chunks(db, document_kind="rfp", document_id=project_file.id)),
                chunks=list_document_chunks(db, document_kind="rfp", document_id=project_file.id),
            )
            for project_file in files
        ],
    )


@router.get("/projects/{project_id}/debug/rfp-chunks", response_model=DebugRfpChunksResponse)
async def read_rfp_chunks(
    project_id: int,
    db: Session = Depends(get_db),
) -> DebugRfpChunksResponse:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    return _build_rfp_chunks_response(db, project_id)


@router.post("/projects/{project_id}/debug/rfp-chunks/rebuild", response_model=DebugRfpChunksResponse)
async def rebuild_rfp_chunks(
    project_id: int,
    db: Session = Depends(get_db),
) -> DebugRfpChunksResponse:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    files = list_project_files(db, project_id)
    for project_file in files:
        rebuild_project_file_chunks(db, project_file)

    return _build_rfp_chunks_response(db, project_id)


@router.get("/projects/{project_id}/debug/prompt-traces", response_model=PromptTraceListResponse)
async def read_prompt_traces(
    project_id: int,
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
) -> PromptTraceListResponse:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    traces = [
        PromptTraceRead.model_validate(trace)
        for trace in list_prompt_traces(project_id=project_id, limit=limit)
    ]
    return PromptTraceListResponse(project_id=project_id, traces=traces)


@router.get("/projects/{project_id}/debug/draft-plan", response_model=DebugPlannerResponse)
async def read_debug_draft_plan(
    project_id: int,
    db: Session = Depends(get_db),
) -> DebugPlannerResponse:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    sections = ensure_project_outline(db, project_id)
    extraction = ensure_rfp_extraction(db, project_id)
    requirements = list_requirement_items(db, project_id)
    evaluation_items = list_evaluation_items(db, project_id)
    assets = list_project_assets(db, project_id)
    asset_text_index = build_asset_text_index(db, assets)
    debug_result = build_draft_plan_debug(
        project_name=project.name,
        sections=sections,
        extraction=extraction,
        requirements=requirements,
        evaluation_items=evaluation_items,
        assets=assets,
        asset_text_index=asset_text_index,
    )

    return DebugPlannerResponse(
        project_id=project_id,
        ready=debug_result.ready,
        warnings=debug_result.warnings,
        sections=[
            DebugPlannerSectionRead(
                section_id=section.section_id,
                heading_text=section.heading_text,
                heading_path=section.heading_path,
                section_tokens=section.section_tokens,
                section_goal=section.section_goal,
                draft_guidance=section.draft_guidance,
                assigned_company_facts=section.assigned_company_facts,
                search_tasks=[
                    DebugPlannerSearchTaskRead(
                        topic=task.topic,
                        reason=task.reason,
                        freshness_required=task.freshness_required,
                        expected_output=task.expected_output,
                    )
                    for task in section.search_tasks
                ],
                requirement_candidates=[
                    DebugPlannerRequirementCandidateRead(
                        requirement_id=item.requirement_id,
                        requirement_no=item.requirement_no,
                        name=item.name,
                        definition=item.definition,
                        details=item.details,
                        score=item.score,
                        matched_tokens=item.matched_tokens,
                        selected=item.selected,
                    )
                    for item in section.requirement_candidates
                ],
                evaluation_candidates=[
                    DebugPlannerEvaluationCandidateRead(
                        evaluation_item_id=item.evaluation_item_id,
                        item=item.item,
                        score_text=item.score_text,
                        notes=item.notes,
                        score=item.score,
                        matched_tokens=item.matched_tokens,
                        selected=item.selected,
                    )
                    for item in section.evaluation_candidates
                ],
                asset_candidates=[
                    DebugPlannerAssetCandidateRead(
                        asset_id=item.asset_id,
                        category=item.category,
                        title=item.title,
                        score=item.score,
                        matched_tokens=item.matched_tokens,
                        compact_heading_match=item.compact_heading_match,
                        selected=item.selected,
                        snippet_previews=item.snippet_previews,
                    )
                    for item in section.asset_candidates
                ],
            )
            for section in debug_result.sections
        ],
    )
