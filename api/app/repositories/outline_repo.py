from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.outline import Citation, OutlineSection


def _clamp_depth(depth: int) -> int:
    return max(1, min(6, depth))


def _normalize_section_snapshots(sections: list[dict]) -> list[dict]:
    counters = [0, 0, 0, 0, 0, 0]
    previous_depth = 0
    normalized_sections: list[dict] = []

    for index, payload in enumerate(sections, start=1):
        desired_depth = _clamp_depth(int(payload.get("depth") or 1))
        normalized_depth = 1 if previous_depth == 0 else min(desired_depth, min(6, previous_depth + 1))
        counters[normalized_depth - 1] += 1
        for position in range(normalized_depth, len(counters)):
            counters[position] = 0

        previous_depth = normalized_depth
        normalized_sections.append(
            {
                **payload,
                "sort_order": index,
                "depth": normalized_depth,
                "display_label": ".".join(str(counter) for counter in counters[:normalized_depth]),
            }
        )

    return normalized_sections


def _normalize_outline_rows(db: Session, sections: list[OutlineSection]) -> list[OutlineSection]:
    changed = False
    normalized = _normalize_section_snapshots(
        [
            {
                "sort_order": section.sort_order,
                "depth": section.depth,
                "display_label": section.display_label,
                "title": section.title,
            }
            for section in sections
        ]
    )

    for section, payload in zip(sections, normalized):
        if section.sort_order != payload["sort_order"]:
            section.sort_order = payload["sort_order"]
            changed = True
        if section.depth != payload["depth"]:
            section.depth = payload["depth"]
            changed = True
        if section.display_label != payload["display_label"]:
            section.display_label = payload["display_label"]
            changed = True

    if changed:
        db.commit()

    return sections


def ensure_project_outline(db: Session, project_id: int) -> list[OutlineSection]:
    return list_outline_sections(db, project_id)


def list_outline_sections(db: Session, project_id: int) -> list[OutlineSection]:
    statement = (
        select(OutlineSection)
        .where(OutlineSection.project_id == project_id)
        .order_by(OutlineSection.sort_order.asc(), OutlineSection.id.asc())
    )
    return _normalize_outline_rows(db, list(db.scalars(statement).all()))


def get_outline_section(db: Session, project_id: int, section_id: int) -> OutlineSection | None:
    statement = select(OutlineSection).where(
        OutlineSection.project_id == project_id, OutlineSection.id == section_id
    )
    return db.scalars(statement).first()


def save_outline_sections(db: Session, project_id: int, sections: list[dict]) -> list[OutlineSection]:
    existing_sections = {section.id: section for section in list_outline_sections(db, project_id)}
    kept_ids: set[int] = set()

    for payload in _normalize_section_snapshots(sections):
        section_id = payload.get("id")
        sort_order = payload["sort_order"]
        depth = payload["depth"]
        display_label = payload["display_label"]

        if section_id and section_id in existing_sections:
            section = existing_sections[section_id]
            section.sort_order = sort_order
            section.depth = depth
            section.display_label = display_label
            section.title = payload["title"]
            kept_ids.add(section.id)
            continue

        section = OutlineSection(
            project_id=project_id,
            sort_order=sort_order,
            depth=depth,
            display_label=display_label,
            title=payload["title"],
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
