from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.project_repo import get_project
from app.schemas.research import (
    ResearchResultRead,
    ResearchRunRequest,
    ResearchRunResponse,
)
from app.services.research_service import ResearchRequest, run_research_requests

router = APIRouter(tags=["research"])


@router.post("/projects/{project_id}/research/run", response_model=ResearchRunResponse)
async def run_project_research(
    project_id: int,
    payload: ResearchRunRequest,
    db: Session = Depends(get_db),
) -> ResearchRunResponse:
    project = get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    requests = [
        ResearchRequest(
            query=item.query,
            purpose=item.purpose,
            reason=item.reason,
            expected_output=item.expected_output,
            allowed_domains=tuple(item.allowed_domains),
            max_results=item.max_results,
            external_web_access=item.external_web_access,
            source_stage=item.source_stage,
            context_summary=item.context_summary
            or "\n".join(
                part
                for part in (
                    f"section_heading={payload.section_heading.strip()}" if payload.section_heading.strip() else "",
                    f"writing_mode={payload.writing_mode.strip()}" if payload.writing_mode.strip() else "",
                    f"unit_pattern={payload.unit_pattern.strip()}" if payload.unit_pattern.strip() else "",
                    f"goal={payload.goal.strip()}" if payload.goal.strip() else "",
                    payload.requirements_summary.strip(),
                )
                if part
            ),
        )
        for item in payload.search_requests
        if item.query.strip()
    ]

    if not requests:
        raise HTTPException(status_code=400, detail="search_requests must include at least one query")

    outcome = run_research_requests(
        requests=requests,
        project_id=project_id,
        trace_kind="research.api",
        trace_metadata={
            "section_heading": payload.section_heading,
            "writing_mode": payload.writing_mode,
            "unit_pattern": payload.unit_pattern,
        },
    )

    return ResearchRunResponse(
        project_id=project_id,
        section_heading=payload.section_heading,
        writing_mode=payload.writing_mode,
        unit_pattern=payload.unit_pattern,
        results=[
            ResearchResultRead(
                query=item.query,
                purpose=item.purpose,
                reason=item.reason,
                expected_output=item.expected_output,
                searched_on=item.searched_on,
                summary=item.summary,
                citations=[
                    {"title": citation.title, "url": citation.url, "snippet": citation.snippet}
                    for citation in item.citations
                ],
                sources=[
                    {"title": source.title, "url": source.url}
                    for source in item.sources
                ],
                source_stage=item.source_stage,
            )
            for item in outcome.results
        ],
        errors=list(outcome.errors),
    )
