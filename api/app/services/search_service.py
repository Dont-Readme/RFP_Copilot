from __future__ import annotations

from app.models.outline import OutlineSection
from app.services.retrieval_service import build_citation_payloads_for_query


def build_citation_payloads(
    *,
    db,
    project_id: int,
    sections: list[OutlineSection],
) -> list[dict]:
    citations: list[dict] = []
    for section in sections:
        citations.extend(
            build_citation_payloads_for_query(
                db,
                project_id=project_id,
                outline_section_id=section.id,
                query=section.title,
            )
        )
    return citations
