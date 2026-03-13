from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.repositories.draft_repo import create_search_task, find_cached_search_task, update_search_task
from app.services.research_service import (
    ResearchCitation,
    ResearchRequest,
    ResearchResult,
    ResearchRunOutcome,
    ResearchSource,
    build_research_query,
    normalize_allowed_domains,
    run_research_request,
)


def _result_from_cached_task(task) -> ResearchResult:
    citations_payload = json.loads(task.citations_json or "[]")
    sources_payload = json.loads(task.sources_json or "[]")
    return ResearchResult(
        query=task.query_text or task.topic,
        purpose=task.purpose or "",
        reason=task.reason or "",
        expected_output=task.expected_output or "",
        searched_on=task.searched_on or "",
        summary=task.result_summary or "",
        citations=tuple(
            ResearchCitation(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("snippet", ""),
            )
            for item in citations_payload
            if item.get("url")
        ),
        sources=tuple(
            ResearchSource(
                title=item.get("title", ""),
                url=item.get("url", ""),
            )
            for item in sources_payload
            if item.get("url")
        ),
        source_stage=task.source_stage or "planned",
    )


def run_project_research_requests(
    *,
    db: Session,
    project_id: int,
    outline_section_id: int,
    unit_key: str,
    requests: list[ResearchRequest],
    trace_kind: str,
    trace_metadata: dict[str, object] | None = None,
) -> ResearchRunOutcome:
    results: list[ResearchResult] = []
    errors: list[str] = []

    for request in requests:
        normalized_query, searched_on = build_research_query(request.query)
        allowed_domains = normalize_allowed_domains(request.allowed_domains)
        allowed_domains_json = json.dumps(allowed_domains, ensure_ascii=False)

        cached_task = find_cached_search_task(
            db,
            project_id=project_id,
            topic=normalized_query,
            purpose=request.purpose,
            allowed_domains_json=allowed_domains_json,
            searched_on=searched_on,
        )
        if cached_task is not None and cached_task.result_summary.strip():
            results.append(_result_from_cached_task(cached_task))
            continue

        task = create_search_task(
            db,
            project_id=project_id,
            outline_section_id=outline_section_id,
            topic=normalized_query,
            unit_key=unit_key,
            purpose=request.purpose,
            reason=request.reason,
            source_stage=request.source_stage,
            freshness_required=True,
            expected_output=request.expected_output,
            allowed_domains=allowed_domains,
            max_results=request.max_results,
            status="running",
        )
        try:
            result = run_research_request(
                request=ResearchRequest(
                    query=normalized_query,
                    purpose=request.purpose,
                    reason=request.reason,
                    expected_output=request.expected_output,
                    allowed_domains=tuple(allowed_domains),
                    max_results=request.max_results,
                    external_web_access=request.external_web_access,
                    source_stage=request.source_stage,
                    context_summary=request.context_summary,
                ),
                project_id=project_id,
                trace_kind=trace_kind,
                trace_metadata=trace_metadata,
            )
        except Exception as exc:
            update_search_task(db, task=task, status="failed", query_text=normalized_query, searched_on=searched_on)
            errors.append(f"{normalized_query}: {exc}")
            continue

        update_search_task(
            db,
            task=task,
            status="done",
            query_text=result.query,
            searched_on=result.searched_on,
            result_summary=result.summary,
            citations_json=json.dumps(
                [
                    {"title": item.title, "url": item.url, "snippet": item.snippet}
                    for item in result.citations
                ],
                ensure_ascii=False,
            ),
            sources_json=json.dumps(
                [{"title": item.title, "url": item.url} for item in result.sources],
                ensure_ascii=False,
            ),
        )
        results.append(result)

    return ResearchRunOutcome(results=tuple(results), errors=tuple(errors))
