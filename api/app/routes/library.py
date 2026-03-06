from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.library_repo import (
    asset_ids_exist,
    create_asset,
    list_assets,
    list_project_assets,
    sync_project_assets,
)
from app.repositories.project_repo import get_project
from app.schemas.library import LibraryAssetRead, ProjectAssetLinkPayload, ProjectAssetLinkResult
from app.services.chunking_service import ensure_library_asset_chunks
from app.services.library_service import save_upload_file, validate_asset_category

router = APIRouter(tags=["library"])


@router.post(
    "/library/assets",
    response_model=LibraryAssetRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_library_asset(
    category: Annotated[str, Form(...)],
    title: Annotated[str | None, Form()] = None,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> LibraryAssetRead:
    normalized_category = validate_asset_category(category)
    filename, mime, path = save_upload_file(file)
    asset_title = (title or "").strip() or filename.rsplit(".", 1)[0]
    asset = create_asset(
        db,
        category=normalized_category,
        title=asset_title,
        filename=filename,
        mime=mime,
        path=path,
    )
    ensure_library_asset_chunks(db, asset)
    return asset


@router.get("/library/assets", response_model=list[LibraryAssetRead])
async def read_library_assets(
    category: str | None = None, db: Session = Depends(get_db)
) -> list[LibraryAssetRead]:
    if category:
        validate_asset_category(category)
    return list_assets(db, category)


@router.get("/projects/{project_id}/assets", response_model=list[LibraryAssetRead])
async def read_project_assets(
    project_id: int, db: Session = Depends(get_db)
) -> list[LibraryAssetRead]:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    return list_project_assets(db, project_id)


@router.post("/projects/{project_id}/assets/link", response_model=ProjectAssetLinkResult)
async def link_project_assets(
    project_id: int,
    payload: ProjectAssetLinkPayload,
    db: Session = Depends(get_db),
) -> ProjectAssetLinkResult:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    if not asset_ids_exist(db, payload.asset_ids):
        raise HTTPException(status_code=404, detail="One or more assets were not found")
    asset_ids = sync_project_assets(db, project_id, payload.asset_ids)
    return ProjectAssetLinkResult(project_id=project_id, asset_ids=asset_ids)
