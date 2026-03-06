from __future__ import annotations

from dataclasses import dataclass

from app.models.outline import OutlineSection
from app.models.rfp import RfpExtraction, RfpRequirementItem
from app.services.retrieval_service import RetrievedChunk, retrieval_tokens, retrieve_project_chunks


@dataclass(frozen=True)
class DraftSectionPlan:
    section: OutlineSection
    heading_text: str
    heading_path: list[str]
    query_text: str
    matched_requirements: list[RfpRequirementItem]
    rfp_sources: list[RetrievedChunk]
    library_sources: list[RetrievedChunk]


@dataclass(frozen=True)
class DraftPlanResult:
    ready: bool
    warnings: list[str]
    sections: list[DraftSectionPlan]


def _heading_text(section: OutlineSection) -> str:
    label = (section.display_label or "").strip()
    title = section.title.strip()
    if label:
        return f"{label} {title}".strip()
    return title


def _build_heading_paths(sections: list[OutlineSection]) -> dict[int, list[str]]:
    paths: dict[int, list[str]] = {}
    stack: list[str] = []

    for section in sections:
        depth = max(1, section.depth)
        stack = stack[: depth - 1]
        stack.append(_heading_text(section))
        paths[section.id] = stack.copy()

    return paths


def _requirement_score(path_text: str, requirement: RfpRequirementItem) -> int:
    query_tokens = retrieval_tokens(path_text)
    if not query_tokens:
        return 0

    name_text = requirement.name.lower()
    definition_text = requirement.definition.lower()
    details_text = requirement.details.lower()
    score = 0
    for token in query_tokens:
        if token in name_text:
            score += 4
        elif token in definition_text:
            score += 2
        elif token in details_text:
            score += 1
    return score


def _match_requirements(
    path_text: str,
    requirements: list[RfpRequirementItem],
    *,
    limit: int = 3,
) -> list[RfpRequirementItem]:
    scored = [
        (requirement, _requirement_score(path_text, requirement)) for requirement in requirements
    ]
    scored.sort(
        key=lambda item: (
            -item[1],
            item[0].sort_order,
            item[0].id,
        )
    )
    matched = [requirement for requirement, score in scored if score > 0]
    return matched[:limit]


def _build_query_text(path: list[str], matched_requirements: list[RfpRequirementItem]) -> str:
    parts = [" ".join(path)]
    if matched_requirements:
        parts.extend(
            f"{requirement.requirement_no} {requirement.name} {requirement.definition}".strip()
            for requirement in matched_requirements
        )
    return "\n".join(part for part in parts if part.strip())


def build_draft_plan(
    *,
    db,
    project_id: int,
    sections: list[OutlineSection],
    extraction: RfpExtraction,
    requirements: list[RfpRequirementItem],
) -> DraftPlanResult:
    warnings: list[str] = []
    if not sections:
        warnings.append("저장된 목차가 없습니다. Outline 페이지에서 목차를 먼저 저장해 주세요.")
    if not extraction.raw_text.strip():
        warnings.append("RFP 추출 결과가 없습니다. RFP 화면에서 추출을 먼저 실행해 주세요.")

    heading_paths = _build_heading_paths(sections)
    section_plans: list[DraftSectionPlan] = []

    for section in sections:
        heading_path = heading_paths.get(section.id, [_heading_text(section)])
        path_text = " ".join(heading_path)
        matched_requirements = _match_requirements(path_text, requirements)
        query_text = _build_query_text(heading_path, matched_requirements)
        rfp_sources = retrieve_project_chunks(
            db,
            project_id=project_id,
            query=query_text,
            limit=3,
            document_kinds={"rfp"},
        )
        library_sources = retrieve_project_chunks(
            db,
            project_id=project_id,
            query=query_text,
            limit=4,
            document_kinds={"library"},
        )
        section_plans.append(
            DraftSectionPlan(
                section=section,
                heading_text=_heading_text(section),
                heading_path=heading_path,
                query_text=query_text,
                matched_requirements=matched_requirements,
                rfp_sources=rfp_sources,
                library_sources=library_sources,
            )
        )

    return DraftPlanResult(
        ready=bool(sections) and bool(extraction.raw_text.strip()),
        warnings=warnings,
        sections=section_plans,
    )


def apply_section_overrides(
    plans: list[DraftSectionPlan],
    *,
    overrides_by_section_id: dict[int, dict[str, set[int]]],
) -> tuple[dict[int, list[RfpRequirementItem]], dict[int, list[RetrievedChunk]]]:
    requirements_by_section: dict[int, list[RfpRequirementItem]] = {}
    sources_by_section: dict[int, list[RetrievedChunk]] = {}

    for plan in plans:
        section_id = plan.section.id
        override = overrides_by_section_id.get(section_id)
        matched_requirements = plan.matched_requirements
        retrieved_sources = [*plan.rfp_sources, *plan.library_sources]

        if override is not None:
            requirement_ids = override["requirement_ids"]
            chunk_ids = override["chunk_ids"]
            matched_requirements = [
                requirement
                for requirement in matched_requirements
                if requirement.id in requirement_ids
            ]
            retrieved_sources = [
                source for source in retrieved_sources if source.chunk.id in chunk_ids
            ]

        requirements_by_section[section_id] = matched_requirements
        sources_by_section[section_id] = retrieved_sources

    return requirements_by_section, sources_by_section
