from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
import re

from openai import OpenAI

from app.core.config import get_settings
from app.services.prompt_trace_service import record_prompt_trace
from app.services.prompts import build_research_request_prompt


class ResearchError(RuntimeError):
    pass


@dataclass(frozen=True)
class ResearchRequest:
    query: str
    purpose: str = ""
    reason: str = ""
    expected_output: str = ""
    allowed_domains: tuple[str, ...] = ()
    max_results: int = 4
    external_web_access: bool = True
    source_stage: str = "planned"
    context_summary: str = ""


@dataclass(frozen=True)
class ResearchCitation:
    title: str
    url: str
    snippet: str


@dataclass(frozen=True)
class ResearchSource:
    title: str
    url: str


@dataclass(frozen=True)
class ResearchResult:
    query: str
    purpose: str
    reason: str
    expected_output: str
    searched_on: str
    summary: str
    citations: tuple[ResearchCitation, ...] = field(default_factory=tuple)
    sources: tuple[ResearchSource, ...] = field(default_factory=tuple)
    source_stage: str = "planned"


@dataclass(frozen=True)
class ResearchRunOutcome:
    results: tuple[ResearchResult, ...]
    errors: tuple[str, ...] = ()


def normalize_allowed_domains(domains: list[str] | tuple[str, ...]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for domain in domains:
        cleaned = re.sub(r"^https?://", "", (domain or "").strip(), flags=re.IGNORECASE).strip("/")
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
    return normalized[:20]


def _normalize_query(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def build_research_query(query: str, *, today: date | None = None) -> tuple[str, str]:
    current_day = today or date.today()
    searched_on = current_day.isoformat()
    normalized_query = _normalize_query(query)
    return normalized_query, searched_on


@lru_cache(maxsize=1)
def _get_client() -> OpenAI:
    settings = get_settings()
    if not settings.openai_api_key:
        raise ResearchError("OPENAI_API_KEY is not set")
    return OpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        timeout=settings.openai_timeout_seconds,
    )


def _line_excerpt(text: str, start_index: int, end_index: int) -> str:
    line_start = text.rfind("\n", 0, start_index) + 1
    line_end = text.find("\n", end_index)
    if line_end == -1:
        line_end = len(text)
    line = text[line_start:line_end].strip()
    line = re.sub(r"^[\-\*\d\.\)\s]+", "", line)
    return re.sub(r"\s+", " ", line).strip()


def _fallback_title_from_url(url: str) -> str:
    return url.split("//", 1)[-1].split("/", 1)[0].strip() or url


def run_research_request(
    *,
    request: ResearchRequest,
    today: date | None = None,
    project_id: int | None = None,
    trace_kind: str = "draft.research",
    trace_metadata: dict[str, object] | None = None,
) -> ResearchResult:
    settings = get_settings()
    client = _get_client()
    normalized_query, searched_on = build_research_query(request.query, today=today)
    if not normalized_query:
        raise ResearchError("Research query is empty")

    prompt_input = build_research_request_prompt(
        query=normalized_query,
        purpose=request.purpose,
        reason=request.reason,
        expected_output=request.expected_output,
        searched_on=searched_on,
        max_results=max(1, min(request.max_results, 8)),
        context_summary=request.context_summary,
    )
    allowed_domains = normalize_allowed_domains(request.allowed_domains)
    if project_id is not None:
        record_prompt_trace(
            project_id=project_id,
            trace_kind=trace_kind,
            model=settings.openai_model_research,
            input_text=prompt_input,
            metadata={
                "query": normalized_query,
                "purpose": request.purpose,
                "source_stage": request.source_stage,
                "allowed_domains": allowed_domains,
                "max_results": request.max_results,
                **(trace_metadata or {}),
            },
        )

    tool_spec: dict[str, object] = {
        "type": "web_search",
        "search_context_size": "low",
        "external_web_access": request.external_web_access,
        "user_location": {
            "type": "approximate",
            "country": "KR",
            "region": "Seoul",
            "city": "Seoul",
            "timezone": "Asia/Seoul",
        },
    }
    if allowed_domains:
        tool_spec["filters"] = {"allowed_domains": allowed_domains}

    try:
        response = client.responses.create(
            model=settings.openai_model_research,
            tools=[tool_spec],
            include=["web_search_call.action.sources"],
            input=prompt_input,
            max_output_tokens=2200,
            reasoning={"effort": "low", "summary": "concise"},
        )
    except Exception as exc:
        raise ResearchError(f"OpenAI web search failed: {exc.__class__.__name__}: {exc}") from exc

    summary_parts: list[str] = []
    citations_by_url: dict[str, ResearchCitation] = {}

    for output_item in response.output:
        if getattr(output_item, "type", "") != "message":
            continue
        for content in getattr(output_item, "content", []):
            if getattr(content, "type", "") != "output_text":
                continue
            text = (getattr(content, "text", "") or "").strip()
            if text:
                summary_parts.append(text)
            for annotation in getattr(content, "annotations", []):
                if getattr(annotation, "type", "") != "url_citation":
                    continue
                url = (getattr(annotation, "url", "") or "").strip()
                if not url:
                    continue
                snippet = _line_excerpt(
                    text,
                    start_index=getattr(annotation, "start_index", 0),
                    end_index=getattr(annotation, "end_index", 0),
                )
                if not snippet:
                    snippet = re.sub(r"\s+", " ", text).strip()[:280]
                citations_by_url[url] = ResearchCitation(
                    title=(getattr(annotation, "title", "") or "").strip() or _fallback_title_from_url(url),
                    url=url,
                    snippet=snippet[:360],
                )

    sources_by_url: dict[str, ResearchSource] = {}
    for output_item in response.output:
        if getattr(output_item, "type", "") != "web_search_call":
            continue
        action = getattr(output_item, "action", None)
        if getattr(action, "type", "") != "search":
            continue
        for source in getattr(action, "sources", []) or []:
            url = (getattr(source, "url", "") or "").strip()
            if not url:
                continue
            sources_by_url[url] = ResearchSource(
                title=(getattr(source, "title", "") or "").strip() or _fallback_title_from_url(url),
                url=url,
            )

    summary = "\n".join(part for part in summary_parts if part).strip()
    if not summary and citations_by_url:
        summary = "\n".join(f"- {item.snippet}" for item in list(citations_by_url.values())[: request.max_results]).strip()
    if not summary:
        raise ResearchError("OpenAI web search returned no usable summary")

    for url, citation in citations_by_url.items():
        sources_by_url.setdefault(url, ResearchSource(title=citation.title, url=url))

    return ResearchResult(
        query=normalized_query,
        purpose=request.purpose,
        reason=request.reason,
        expected_output=request.expected_output,
        searched_on=searched_on,
        summary=summary[:2400],
        citations=tuple(list(citations_by_url.values())[: max(1, min(request.max_results, 8))]),
        sources=tuple(sources_by_url.values()),
        source_stage=request.source_stage,
    )


def run_research_requests(
    *,
    requests: list[ResearchRequest],
    today: date | None = None,
    project_id: int | None = None,
    trace_kind: str = "draft.research",
    trace_metadata: dict[str, object] | None = None,
) -> ResearchRunOutcome:
    results: list[ResearchResult] = []
    errors: list[str] = []
    seen: set[tuple[str, str, tuple[str, ...], str]] = set()

    for request in requests:
        normalized_query, _ = build_research_query(request.query, today=today)
        allowed_domains = tuple(normalize_allowed_domains(request.allowed_domains))
        dedupe_key = (
            normalized_query,
            request.purpose.strip(),
            allowed_domains,
            request.source_stage.strip(),
        )
        if not normalized_query or dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        try:
            results.append(
                run_research_request(
                    request=ResearchRequest(
                        query=normalized_query,
                        purpose=request.purpose,
                        reason=request.reason,
                        expected_output=request.expected_output,
                        allowed_domains=allowed_domains,
                        max_results=request.max_results,
                        external_web_access=request.external_web_access,
                        source_stage=request.source_stage,
                        context_summary=request.context_summary,
                    ),
                    today=today,
                    project_id=project_id,
                    trace_kind=trace_kind,
                    trace_metadata=trace_metadata,
                )
            )
        except ResearchError as exc:
            errors.append(f"{normalized_query}: {exc}")

    return ResearchRunOutcome(results=tuple(results), errors=tuple(errors))
