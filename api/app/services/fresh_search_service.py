from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re

from app.services.research_service import ResearchRequest, run_research_requests


class FreshSearchError(RuntimeError):
    pass


@dataclass(frozen=True)
class FreshSearchResult:
    source_title: str
    source_url: str
    snippet: str
    searched_on: str
    query_text: str


def build_fresh_search_query(topic: str, *, today: date | None = None) -> tuple[str, str]:
    current_day = today or date.today()
    searched_on = current_day.isoformat()
    normalized_topic = re.sub(r"\s+", " ", topic).strip()
    query_text = f"{normalized_topic} | latest as of {searched_on}"
    return query_text, searched_on


def run_fresh_search(
    *,
    topic: str,
    today: date | None = None,
    limit: int = 3,
    project_id: int | None = None,
    trace_metadata: dict[str, object] | None = None,
) -> list[FreshSearchResult]:
    query_text, searched_on = build_fresh_search_query(topic, today=today)
    outcome = run_research_requests(
        requests=[
            ResearchRequest(
                query=topic,
                purpose="general_evidence",
                reason="최신 정보 확인",
                expected_output="최신 검색 핵심 bullet",
                max_results=limit,
                source_stage="planned",
            )
        ],
        today=today,
        project_id=project_id,
        trace_kind="draft.search",
        trace_metadata=trace_metadata,
    )
    if outcome.errors and not outcome.results:
        raise FreshSearchError(outcome.errors[0])

    results_by_url: dict[str, FreshSearchResult] = {}
    for result in outcome.results:
        for citation in result.citations:
            results_by_url[citation.url] = FreshSearchResult(
                source_title=citation.title,
                source_url=citation.url,
                snippet=citation.snippet[:320],
                searched_on=result.searched_on,
                query_text=query_text,
            )
        for source in result.sources:
            results_by_url.setdefault(
                source.url,
                FreshSearchResult(
                    source_title=source.title,
                    source_url=source.url,
                    snippet="최신 검색 출처가 확인되었습니다.",
                    searched_on=searched_on,
                    query_text=query_text,
                ),
            )

    results = list(results_by_url.values())
    if not results:
        raise FreshSearchError("OpenAI web search returned no cited sources")
    return results[:limit]
