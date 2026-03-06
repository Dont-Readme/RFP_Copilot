from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.repositories.draft_repo import ensure_project_workspace, list_draft_sections, list_questions
from app.repositories.export_repo import create_export_session, get_export_session
from app.repositories.mapping_repo import list_warnings
from app.repositories.project_repo import get_project
from app.repositories.evaluation_repo import list_evaluation_items
from app.repositories.rfp_repo import ensure_rfp_extraction, list_requirement_items
from app.schemas.export import ExportCreateRequest, ExportPreviewRead, ExportSessionRead
from app.services.export_service import create_export_artifacts

router = APIRouter(tags=["export"])


def _resolve_data_path(relative_path: str) -> Path:
    settings = get_settings()
    return settings.app_data_dir / relative_path


@router.post("/projects/{project_id}/export", response_model=ExportSessionRead)
async def create_export(
    project_id: int, payload: ExportCreateRequest, db: Session = Depends(get_db)
) -> ExportSessionRead:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    ensure_project_workspace(db, project)
    draft_sections = list_draft_sections(db, project_id)
    if not draft_sections:
        raise HTTPException(status_code=400, detail="No draft sections available")
    draft_section = draft_sections[0]
    questions = [question.__dict__ for question in list_questions(db, project_id)]
    warnings = [warning.__dict__ for warning in list_warnings(db, project_id)]
    extraction = ensure_rfp_extraction(db, project_id)

    session_id, preview_md_path, files_json = create_export_artifacts(
        project_id=project_id,
        project_name=project.name,
        formats=payload.formats,
        draft_content=draft_section.content_md,
        questions=questions,
        warnings=warnings,
        extraction_summary={
            "project_summary_text": extraction.project_summary_text,
            "requirements_count": len(list_requirement_items(db, project_id)),
            "evaluation_count": len(list_evaluation_items(db, project_id)),
        },
    )
    return create_export_session(
        db,
        session_id=session_id,
        project_id=project_id,
        preview_md_path=preview_md_path,
        files_json=files_json,
    )


@router.get(
    "/projects/{project_id}/export/{export_session_id}/preview",
    response_model=ExportPreviewRead,
)
async def read_export_preview(
    project_id: int, export_session_id: str, db: Session = Depends(get_db)
) -> ExportPreviewRead:
    export_session = get_export_session(db, project_id, export_session_id)
    if export_session is None:
        raise HTTPException(status_code=404, detail=f"Export session {export_session_id} not found")
    files = json.loads(export_session.files_json)
    preview_md = _resolve_data_path(export_session.preview_md_path).read_text(
        encoding="utf-8", errors="ignore"
    )
    return ExportPreviewRead(
        export_session_id=export_session.id,
        preview_md=preview_md,
        formats=list(files.keys()),
    )


@router.get("/projects/{project_id}/export/{export_session_id}/download")
async def download_export_file(
    project_id: int,
    export_session_id: str,
    format: str = Query(...),
    db: Session = Depends(get_db),
):
    export_session = get_export_session(db, project_id, export_session_id)
    if export_session is None:
        raise HTTPException(status_code=404, detail=f"Export session {export_session_id} not found")
    files = json.loads(export_session.files_json)
    if format not in files:
        raise HTTPException(status_code=404, detail=f"Format {format} not available")

    absolute_path = _resolve_data_path(files[format])
    if not absolute_path.exists():
        raise HTTPException(status_code=404, detail=f"Export file for {format} not found")
    return FileResponse(path=absolute_path, filename=absolute_path.name)
