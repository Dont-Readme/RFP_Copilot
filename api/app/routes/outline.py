from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.outline_repo import (
    ensure_project_outline,
    get_outline_section,
    list_outline_sections,
    list_citations,
    replace_citations_for_sections,
    save_outline_sections,
)
from app.repositories.project_repo import get_project
from app.schemas.outline import (
    CitationRead,
    OutlineSaveRequest,
    OutlineSectionRead,
    SearchRunRequest,
    SearchRunResponse,
)
from app.services.search_service import build_citation_payloads

router = APIRouter(tags=["outline"])


@router.get("/projects/{project_id}/outline", response_model=list[OutlineSectionRead])
async def read_outline(
    project_id: int, db: Session = Depends(get_db)
) -> list[OutlineSectionRead]:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    return ensure_project_outline(db, project_id)


@router.post("/projects/{project_id}/outline", response_model=list[OutlineSectionRead])
async def save_outline(
    project_id: int, payload: OutlineSaveRequest, db: Session = Depends(get_db)
) -> list[OutlineSectionRead]:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    return save_outline_sections(
        db,
        project_id,
        [section.model_dump() for section in payload.sections],
    )


@router.get("/projects/{project_id}/search/citations", response_model=list[CitationRead])
async def read_citations(
    project_id: int,
    section_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[CitationRead]:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    section_ids = [section_id] if section_id is not None else None
    return list_citations(db, project_id, section_ids=section_ids)


@router.post("/projects/{project_id}/search/run", response_model=SearchRunResponse)
async def run_search(
    project_id: int,
    payload: SearchRunRequest,
    db: Session = Depends(get_db),
) -> SearchRunResponse:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    sections = list_outline_sections(db, project_id)
    if payload.section_ids:
        target_sections = []
        for section_id in payload.section_ids:
            section = get_outline_section(db, project_id, section_id)
            if section is None:
                raise HTTPException(status_code=404, detail=f"Outline section {section_id} not found")
            target_sections.append(section)
    else:
        target_sections = sections

    if not target_sections:
        raise HTTPException(status_code=400, detail="No outline sections selected for search")

    citations = replace_citations_for_sections(
        db,
        project_id=project_id,
        section_ids=[section.id for section in target_sections],
        citations=build_citation_payloads(
            db=db,
            project_id=project_id,
            sections=target_sections,
        ),
    )
    return SearchRunResponse(
        project_id=project_id,
        section_ids=[section.id for section in target_sections],
        citations=[CitationRead.model_validate(citation) for citation in citations],
    )
