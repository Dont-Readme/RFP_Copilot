from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.export import ExportSession


def create_export_session(
    db: Session,
    *,
    session_id: str,
    project_id: int,
    preview_md_path: str,
    files_json: str,
    status: str = "ready",
) -> ExportSession:
    export_session = ExportSession(
        id=session_id,
        project_id=project_id,
        preview_md_path=preview_md_path,
        files_json=files_json,
        status=status,
    )
    db.add(export_session)
    db.commit()
    db.refresh(export_session)
    return export_session


def get_export_session(db: Session, project_id: int, session_id: str) -> ExportSession | None:
    statement = select(ExportSession).where(
        ExportSession.project_id == project_id, ExportSession.id == session_id
    )
    return db.scalars(statement).first()


def get_latest_export_session(db: Session, project_id: int) -> ExportSession | None:
    statement = (
        select(ExportSession)
        .where(ExportSession.project_id == project_id)
        .order_by(desc(ExportSession.created_at))
    )
    return db.scalars(statement).first()
