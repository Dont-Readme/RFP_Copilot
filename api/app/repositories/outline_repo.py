from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.outline import Citation, OutlineSection

DEFAULT_OUTLINE_SECTIONS = [
    {"title": "제안 개요", "needs_search": False},
    {"title": "수행 전략", "needs_search": True},
    {"title": "기대 효과", "needs_search": True},
]


def ensure_project_outline(db: Session, project_id: int) -> list[OutlineSection]:
    count = db.scalar(
        select(func.count()).select_from(OutlineSection).where(OutlineSection.project_id == project_id)
    )
    if count:
        return list_outline_sections(db, project_id)

    db.add_all(
        [
            OutlineSection(
                project_id=project_id,
                title=section["title"],
                needs_search=section["needs_search"],
                sort_order=index,
            )
            for index, section in enumerate(DEFAULT_OUTLINE_SECTIONS, start=1)
        ]
    )
    db.commit()
    return list_outline_sections(db, project_id)


def list_outline_sections(db: Session, project_id: int) -> list[OutlineSection]:
    statement = (
        select(OutlineSection)
        .where(OutlineSection.project_id == project_id)
        .order_by(OutlineSection.sort_order.asc(), OutlineSection.id.asc())
    )
    return list(db.scalars(statement).all())


def get_outline_section(db: Session, project_id: int, section_id: int) -> OutlineSection | None:
    statement = select(OutlineSection).where(
        OutlineSection.project_id == project_id, OutlineSection.id == section_id
    )
    return db.scalars(statement).first()


def save_outline_sections(db: Session, project_id: int, sections: list[dict]) -> list[OutlineSection]:
    existing_sections = {section.id: section for section in list_outline_sections(db, project_id)}
    kept_ids: set[int] = set()

    for index, payload in enumerate(sections, start=1):
        section_id = payload.get("id")
        parent_id = payload.get("parent_id")
        sort_order = payload.get("sort_order") or index

        if section_id and section_id in existing_sections:
            section = existing_sections[section_id]
            section.parent_id = parent_id
            section.sort_order = sort_order
            section.title = payload["title"]
            section.needs_search = payload.get("needs_search", False)
            kept_ids.add(section.id)
            continue

        section = OutlineSection(
            project_id=project_id,
            parent_id=parent_id,
            sort_order=sort_order,
            title=payload["title"],
            needs_search=payload.get("needs_search", False),
        )
        db.add(section)
        db.flush()
        kept_ids.add(section.id)

    removed_ids = set(existing_sections) - kept_ids
    if removed_ids:
        db.execute(
            delete(Citation).where(
                Citation.project_id == project_id,
                Citation.outline_section_id.in_(removed_ids),
            )
        )
        db.execute(
            delete(OutlineSection).where(
                OutlineSection.project_id == project_id,
                OutlineSection.id.in_(removed_ids),
            )
        )

    db.commit()
    return list_outline_sections(db, project_id)


def list_citations(
    db: Session, project_id: int, section_ids: list[int] | None = None
) -> list[Citation]:
    statement = (
        select(Citation)
        .where(Citation.project_id == project_id)
        .order_by(Citation.outline_section_id.asc(), Citation.id.asc())
    )
    if section_ids:
        statement = statement.where(Citation.outline_section_id.in_(section_ids))
    return list(db.scalars(statement).all())


def replace_citations_for_sections(
    db: Session,
    *,
    project_id: int,
    section_ids: list[int],
    citations: list[dict],
) -> list[Citation]:
    db.execute(
        delete(Citation).where(
            Citation.project_id == project_id,
            Citation.outline_section_id.in_(section_ids),
        )
    )
    db.add_all(
        [
            Citation(
                project_id=project_id,
                outline_section_id=citation["outline_section_id"],
                source_title=citation["source_title"],
                source_url=citation["source_url"],
                snippet=citation["snippet"],
            )
            for citation in citations
        ]
    )
    db.commit()
    return list_citations(db, project_id, section_ids=section_ids)
