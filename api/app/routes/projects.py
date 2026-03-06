from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.draft_repo import ensure_project_workspace
from app.repositories.outline_repo import ensure_project_outline
from app.repositories.project_repo import (
    create_project,
    delete_project,
    get_project,
    list_projects,
    update_project,
)
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectRead])
async def read_projects(db: Session = Depends(get_db)) -> list[ProjectRead]:
    return list_projects(db)


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project_endpoint(
    payload: ProjectCreate, db: Session = Depends(get_db)
) -> ProjectRead:
    project = create_project(db, payload.name)
    ensure_project_outline(db, project.id)
    ensure_project_workspace(db, project)
    return project


@router.get("/{project_id}", response_model=ProjectRead)
async def read_project(project_id: int, db: Session = Depends(get_db)) -> ProjectRead:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    return project


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project_endpoint(
    project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db)
) -> ProjectRead:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    return update_project(db, project, payload.name)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project_endpoint(project_id: int, db: Session = Depends(get_db)) -> None:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    delete_project(db, project)
