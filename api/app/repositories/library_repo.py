from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.library import LibraryAsset, ProjectAssetLink


def list_assets(db: Session, category: str | None = None) -> list[LibraryAsset]:
    statement = select(LibraryAsset).order_by(LibraryAsset.created_at.desc())
    if category:
        statement = statement.where(LibraryAsset.category == category)
    return list(db.scalars(statement).all())


def create_asset(
    db: Session,
    *,
    category: str,
    title: str,
    filename: str,
    mime: str,
    path: str,
    owner_user_id: str = "local",
) -> LibraryAsset:
    asset = LibraryAsset(
        category=category,
        title=title,
        filename=filename,
        mime=mime,
        path=path,
        owner_user_id=owner_user_id,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def list_project_assets(db: Session, project_id: int) -> list[LibraryAsset]:
    statement = (
        select(LibraryAsset)
        .join(ProjectAssetLink, ProjectAssetLink.asset_id == LibraryAsset.id)
        .where(ProjectAssetLink.project_id == project_id)
        .order_by(ProjectAssetLink.created_at.desc())
    )
    return list(db.scalars(statement).all())


def get_project_asset_ids(db: Session, project_id: int) -> list[int]:
    statement = select(ProjectAssetLink.asset_id).where(ProjectAssetLink.project_id == project_id)
    return list(db.scalars(statement).all())


def sync_project_assets(db: Session, project_id: int, asset_ids: list[int]) -> list[int]:
    desired_ids = sorted(set(asset_ids))
    current_ids = set(get_project_asset_ids(db, project_id))
    desired_set = set(desired_ids)

    if current_ids - desired_set:
        db.execute(
            delete(ProjectAssetLink).where(
                ProjectAssetLink.project_id == project_id,
                ProjectAssetLink.asset_id.in_(current_ids - desired_set),
            )
        )

    for asset_id in desired_set - current_ids:
        db.add(ProjectAssetLink(project_id=project_id, asset_id=asset_id))

    db.commit()
    return desired_ids


def asset_ids_exist(db: Session, asset_ids: list[int]) -> bool:
    if not asset_ids:
        return True

    found_ids = set(
        db.scalars(select(LibraryAsset.id).where(LibraryAsset.id.in_(asset_ids))).all()
    )
    return found_ids == set(asset_ids)
