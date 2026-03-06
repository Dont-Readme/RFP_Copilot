from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy import delete, desc, select
from sqlalchemy.orm import Session

from app.models.rfp import ProjectFile, RfpExtraction, RfpRequirementItem


def create_project_file(
    db: Session,
    *,
    project_id: int,
    filename: str,
    mime: str,
    path: str,
    size: int,
    kind: str = "rfp",
    role: str = "other",
) -> ProjectFile:
    project_file = ProjectFile(
        project_id=project_id,
        filename=filename,
        mime=mime,
        path=path,
        size=size,
        kind=kind,
        role=role,
    )
    db.add(project_file)
    db.commit()
    db.refresh(project_file)
    return project_file


def list_project_files(db: Session, project_id: int, kind: str = "rfp") -> list[ProjectFile]:
    statement = (
        select(ProjectFile)
        .where(ProjectFile.project_id == project_id, ProjectFile.kind == kind)
        .order_by(ProjectFile.created_at.asc(), ProjectFile.id.asc())
    )
    return list(db.scalars(statement).all())


def get_latest_project_file(db: Session, project_id: int, kind: str = "rfp") -> ProjectFile | None:
    statement = (
        select(ProjectFile)
        .where(ProjectFile.project_id == project_id, ProjectFile.kind == kind)
        .order_by(desc(ProjectFile.created_at))
    )
    return db.scalars(statement).first()


def get_project_file(db: Session, project_id: int, file_id: int, kind: str = "rfp") -> ProjectFile | None:
    statement = select(ProjectFile).where(
        ProjectFile.project_id == project_id,
        ProjectFile.kind == kind,
        ProjectFile.id == file_id,
    )
    return db.scalars(statement).first()


def delete_project_file(db: Session, project_file: ProjectFile) -> None:
    db.delete(project_file)
    db.commit()


def ensure_rfp_extraction(db: Session, project_id: int) -> RfpExtraction:
    extraction = db.get(RfpExtraction, project_id)
    if extraction is not None:
        return extraction

    extraction = RfpExtraction(project_id=project_id)
    db.add(extraction)
    db.commit()
    db.refresh(extraction)
    return extraction


def list_requirement_items(db: Session, project_id: int) -> list[RfpRequirementItem]:
    statement = (
        select(RfpRequirementItem)
        .where(RfpRequirementItem.project_id == project_id)
        .order_by(RfpRequirementItem.sort_order.asc(), RfpRequirementItem.id.asc())
    )
    return list(db.scalars(statement).all())


def replace_requirement_items(
    db: Session, project_id: int, items: list[dict]
) -> list[RfpRequirementItem]:
    db.execute(delete(RfpRequirementItem).where(RfpRequirementItem.project_id == project_id))
    db.add_all(
        [
            RfpRequirementItem(
                project_id=project_id,
                sort_order=index,
                requirement_no=item.get("requirement_no", ""),
                name=item.get("name", ""),
                definition=item.get("definition", ""),
                details=item.get("details", ""),
            )
            for index, item in enumerate(items, start=1)
        ]
    )
    db.commit()
    return list_requirement_items(db, project_id)


def update_rfp_extraction(
    db: Session, project_id: int, payload: Mapping[str, object]
) -> RfpExtraction:
    extraction = ensure_rfp_extraction(db, project_id)
    for key, value in payload.items():
        setattr(extraction, key, value)
    db.commit()
    db.refresh(extraction)
    return extraction
