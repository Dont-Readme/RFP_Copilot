from __future__ import annotations

import re
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.repositories.chunk_repo import delete_document_chunks
from app.repositories.evaluation_repo import list_evaluation_items, replace_evaluation_items
from app.repositories.project_repo import get_project
from app.repositories.rfp_repo import (
    create_project_file,
    delete_project_file,
    ensure_rfp_extraction,
    get_project_file,
    list_project_files,
    list_requirement_items,
    replace_requirement_items,
    update_rfp_extraction,
)
from app.schemas.rfp import (
    ProjectFileRead,
    RfpEvaluationItemRead,
    RfpExtractionRead,
    RfpExtractionUpdate,
    RfpFileRole,
    RfpFileUploadResponse,
    RfpRequirementItemRead,
)
from app.services.chunking_service import ensure_project_file_chunks
from app.services.library_service import save_upload_file
from app.services.llm_service import LLMService, get_llm_service
from app.services.rfp_service import FileChunkBundle, RfpExtractionError, extract_rfp_payload

router = APIRouter(tags=["rfp"])

RFP_FILE_ROLES: tuple[RfpFileRole, ...] = ("notice", "sow", "rfp", "requirements", "other")


def _parse_weight(score_text: str) -> float | None:
    match = re.search(r"\d+(?:\.\d+)?", score_text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _format_score_text(item) -> str:
    score_text = (item.score_text or "").strip()
    if score_text:
        return score_text
    if item.weight is None:
        return ""
    if float(item.weight).is_integer():
        return str(int(item.weight))
    return f"{item.weight:g}"


def _validate_file_role(role: str) -> str:
    if role not in RFP_FILE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported RFP file role: {role}",
        )
    return role


def _build_rfp_response(db: Session, project_id: int) -> RfpExtractionRead:
    extraction = ensure_rfp_extraction(db, project_id)
    files = list_project_files(db, project_id)
    requirements = list_requirement_items(db, project_id)
    evaluation_items = list_evaluation_items(db, project_id)
    return RfpExtractionRead(
        project_id=extraction.project_id,
        status=extraction.status,
        raw_text=extraction.raw_text,
        project_summary_text=extraction.project_summary_text,
        ocr_required=extraction.ocr_required,
        updated_at=extraction.updated_at,
        files=[ProjectFileRead.model_validate(project_file) for project_file in files],
        requirements=[RfpRequirementItemRead.model_validate(item) for item in requirements],
        evaluation_items=[
            RfpEvaluationItemRead(
                id=item.id,
                project_id=item.project_id,
                item=item.title,
                score=_format_score_text(item),
                notes=item.description,
                created_at=item.created_at,
            )
            for item in evaluation_items
        ],
    )


def _build_extraction_bundles(db: Session, project_id: int) -> list[FileChunkBundle]:
    bundles: list[FileChunkBundle] = []
    for project_file in list_project_files(db, project_id):
        chunking_result = ensure_project_file_chunks(db, project_file)
        bundles.append(
            FileChunkBundle(
                project_file=project_file,
                raw_text=chunking_result.raw_text,
                chunks=chunking_result.chunks,
            )
        )
    return bundles


def _extract_and_store_rfp(
    db: Session,
    *,
    project_id: int,
    llm_service: LLMService,
) -> RfpExtractionRead:
    bundles = _build_extraction_bundles(db, project_id)
    if not bundles:
        raise HTTPException(status_code=404, detail="No RFP files have been uploaded yet")

    try:
        payload, requirements, evaluation_items = extract_rfp_payload(
            bundles=bundles,
            llm_service=llm_service,
        )
    except RfpExtractionError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=f"OpenAI extraction failed: {exc}",
        ) from exc

    update_rfp_extraction(db, project_id, payload)
    replace_requirement_items(db, project_id, requirements)
    replace_evaluation_items(
        db,
        project_id,
        [
            {
                "code": f"EV-{index:02d}",
                "title": item.get("item", "").strip() or f"평가항목 {index}",
                "score_text": item.get("score", "").strip(),
                "description": item.get("notes", "").strip(),
                "weight": _parse_weight(item.get("score", "")),
            }
            for index, item in enumerate(evaluation_items, start=1)
        ],
    )
    return _build_rfp_response(db, project_id)


def _delete_uploaded_file(relative_path: str) -> None:
    settings = get_settings()
    absolute_path = settings.app_data_dir / relative_path
    if absolute_path.exists():
        absolute_path.unlink()


@router.get("/projects/{project_id}/rfp/files", response_model=list[ProjectFileRead])
async def read_rfp_files(
    project_id: int,
    db: Session = Depends(get_db),
) -> list[ProjectFileRead]:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    return [ProjectFileRead.model_validate(project_file) for project_file in list_project_files(db, project_id)]


@router.post(
    "/projects/{project_id}/rfp/files",
    response_model=RfpFileUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_rfp_file(
    project_id: int,
    role: Annotated[str, Form(...)],
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> RfpFileUploadResponse:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    normalized_role = _validate_file_role(role)
    filename, mime, relative_path = save_upload_file(file)
    settings = get_settings()
    absolute_path = settings.app_data_dir / relative_path
    project_file = create_project_file(
        db,
        project_id=project_id,
        filename=filename,
        mime=mime,
        path=relative_path,
        size=absolute_path.stat().st_size,
        role=normalized_role,
    )
    ensure_project_file_chunks(db, project_file)

    return RfpFileUploadResponse(
        extraction=_build_rfp_response(db, project_id),
        file=ProjectFileRead.model_validate(project_file),
    )


@router.delete("/projects/{project_id}/rfp/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rfp_file_endpoint(
    project_id: int,
    file_id: int,
    db: Session = Depends(get_db),
) -> None:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    project_file = get_project_file(db, project_id, file_id)
    if project_file is None:
        raise HTTPException(status_code=404, detail=f"RFP file {file_id} not found")

    relative_path = project_file.path
    delete_document_chunks(db, document_kind="rfp", document_id=project_file.id)
    delete_project_file(db, project_file)
    _delete_uploaded_file(relative_path)
    if not list_project_files(db, project_id):
        update_rfp_extraction(
            db,
            project_id,
            {
                "status": "draft",
                "raw_text": "",
                "project_summary_text": "",
                "ocr_required": False,
                "eligibility_text": "",
                "submission_docs_text": "",
                "evaluation_overview_text": "",
                "format_rules_text": "",
                "deadline_iso": None,
                "contact_text": "",
                "notes_text": "",
                "source_file_path": None,
            },
        )
        replace_requirement_items(db, project_id, [])
        replace_evaluation_items(db, project_id, [])


@router.get("/projects/{project_id}/rfp/extraction", response_model=RfpExtractionRead)
async def read_rfp_extraction(
    project_id: int,
    db: Session = Depends(get_db),
) -> RfpExtractionRead:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    return _build_rfp_response(db, project_id)


@router.post("/projects/{project_id}/rfp/extract", response_model=RfpExtractionRead)
async def rerun_rfp_extraction(
    project_id: int,
    db: Session = Depends(get_db),
    llm_service: LLMService = Depends(get_llm_service),
) -> RfpExtractionRead:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    return _extract_and_store_rfp(db, project_id=project_id, llm_service=llm_service)


@router.patch("/projects/{project_id}/rfp/extraction", response_model=RfpExtractionRead)
async def update_rfp_extraction_endpoint(
    project_id: int,
    payload: RfpExtractionUpdate,
    db: Session = Depends(get_db),
) -> RfpExtractionRead:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    update_rfp_extraction(
        db,
        project_id,
        {
            "status": payload.status,
            "raw_text": payload.raw_text,
            "project_summary_text": payload.project_summary_text,
            "ocr_required": payload.ocr_required,
        },
    )
    replace_requirement_items(
        db,
        project_id,
        [item.model_dump() for item in payload.requirements],
    )
    replace_evaluation_items(
        db,
        project_id,
        [
            {
                "code": f"EV-{index:02d}",
                "title": item.item.strip() or f"평가항목 {index}",
                "score_text": item.score.strip(),
                "description": item.notes.strip(),
                "weight": _parse_weight(item.score),
            }
            for index, item in enumerate(payload.evaluation_items, start=1)
        ],
    )
    return _build_rfp_response(db, project_id)


@router.post(
    "/projects/{project_id}/rfp/upload",
    response_model=RfpFileUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_rfp_backward_compat(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> RfpFileUploadResponse:
    return await upload_rfp_file(
        project_id=project_id,
        role="other",
        file=file,
        db=db,
    )
