from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.mapping import EvalMapping, MappingWarning


def replace_mapping_results(
    db: Session,
    *,
    project_id: int,
    mappings: list[dict],
    warnings: list[dict],
) -> tuple[list[EvalMapping], list[MappingWarning]]:
    db.execute(delete(EvalMapping).where(EvalMapping.project_id == project_id))
    db.execute(delete(MappingWarning).where(MappingWarning.project_id == project_id))

    db.add_all([EvalMapping(project_id=project_id, **item) for item in mappings])
    db.add_all([MappingWarning(project_id=project_id, **item) for item in warnings])
    db.commit()
    return list_mappings(db, project_id), list_warnings(db, project_id)


def list_mappings(db: Session, project_id: int) -> list[EvalMapping]:
    statement = (
        select(EvalMapping)
        .where(EvalMapping.project_id == project_id)
        .order_by(EvalMapping.created_at.asc(), EvalMapping.id.asc())
    )
    return list(db.scalars(statement).all())


def list_warnings(db: Session, project_id: int) -> list[MappingWarning]:
    statement = (
        select(MappingWarning)
        .where(MappingWarning.project_id == project_id)
        .order_by(MappingWarning.created_at.asc(), MappingWarning.id.asc())
    )
    return list(db.scalars(statement).all())
