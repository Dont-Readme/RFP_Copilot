from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.draft_repo import ensure_project_workspace, list_draft_sections
from app.repositories.evaluation_repo import list_evaluation_items
from app.repositories.mapping_repo import list_mappings, list_warnings, replace_mapping_results
from app.repositories.project_repo import get_project
from app.schemas.mapping import MappingResultRead, MappingRunRequest
from app.schemas.rfp import RfpEvaluationItemRead
from app.services.mapping_service import build_mapping_results

router = APIRouter(tags=["mapping"])


def _serialize_mapping_result(
    *,
    strategy: str,
    evaluation_items: list,
    mappings: list,
    warnings: list,
) -> MappingResultRead:
    return MappingResultRead(
        strategy=strategy,
        evaluation_items=[
            RfpEvaluationItemRead(
                id=item.id,
                project_id=item.project_id,
                item=item.title,
                score=getattr(item, "score_text", "") or "",
                notes=item.description or "",
                created_at=item.created_at,
            )
            for item in evaluation_items
        ],
        mappings=mappings,
        warnings=warnings,
    )


@router.post("/projects/{project_id}/mapping/run", response_model=MappingResultRead)
async def run_mapping(
    project_id: int,
    payload: MappingRunRequest,
    db: Session = Depends(get_db),
) -> MappingResultRead:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    ensure_project_workspace(db, project)
    evaluation_items = list_evaluation_items(db, project_id)
    draft_sections = list_draft_sections(db, project_id)
    if not draft_sections:
        raise HTTPException(status_code=400, detail="No draft sections available")
    draft_section = draft_sections[0]

    mappings_payload, warnings_payload = build_mapping_results(
        draft_section_id=draft_section.id,
        draft_content=draft_section.content_md,
        evaluation_items=[
            {
                "id": item.id,
                "title": item.title,
                "description": item.description,
            }
            for item in evaluation_items
        ],
    )
    mappings, warnings = replace_mapping_results(
        db,
        project_id=project_id,
        mappings=mappings_payload,
        warnings=warnings_payload,
    )
    return _serialize_mapping_result(
        strategy=payload.strategy,
        evaluation_items=evaluation_items,
        mappings=mappings,
        warnings=warnings,
    )


@router.get("/projects/{project_id}/mapping", response_model=MappingResultRead)
async def read_mapping(project_id: int, db: Session = Depends(get_db)) -> MappingResultRead:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    evaluation_items = list_evaluation_items(db, project_id)
    return _serialize_mapping_result(
        strategy="rules",
        evaluation_items=evaluation_items,
        mappings=list_mappings(db, project_id),
        warnings=list_warnings(db, project_id),
    )
