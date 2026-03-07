from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from functools import lru_cache
import re

from openai import OpenAI

from app.core.config import get_settings


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


@lru_cache(maxsize=1)
def _get_client() -> OpenAI:
    settings = get_settings()
    if not settings.openai_api_key:
        raise FreshSearchError("OPENAI_API_KEY is not set")
    return OpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        timeout=settings.openai_timeout_seconds,
    )


def _build_web_search_prompt(*, topic: str, searched_on: str, limit: int) -> str:
    return f"""
오늘 날짜는 {searched_on}입니다.
반드시 web search를 사용해서 아래 주제의 최신 정보를 확인하세요.

주제:
{topic}

지침:
- 최신성 판단은 반드시 위 절대 날짜를 기준으로 하세요.
- 주제와 직접 관련된 정보만 남기고, 일반적인 주변 뉴스는 제외하세요.
- 신뢰 가능한 웹 출처를 우선하세요.
- 확인된 사실만 한국어로 간단히 정리하세요.
- 최대 {limit}개의 bullet만 작성하세요.
- 각 bullet는 하나의 사실만 쓰고, 웹 인용이 붙도록 작성하세요.
- 정보가 부족하면 무리해서 채우지 마세요.
""".strip()


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


def run_fresh_search(
    *,
    topic: str,
    today: date | None = None,
    limit: int = 3,
) -> list[FreshSearchResult]:
    settings = get_settings()
    client = _get_client()
    query_text, searched_on = build_fresh_search_query(topic, today=today)

    try:
        response = client.responses.create(
            model=settings.openai_model_research,
            tools=[
                {
                    "type": "web_search",
                    "search_context_size": "low",
                    "user_location": {
                        "type": "approximate",
                        "country": "KR",
                        "region": "Seoul",
                        "city": "Seoul",
                        "timezone": "Asia/Seoul",
                    },
                }
            ],
            include=["web_search_call.action.sources"],
            input=_build_web_search_prompt(topic=topic, searched_on=searched_on, limit=limit),
            max_output_tokens=1600,
            reasoning={"effort": "low", "summary": "concise"},
        )
    except Exception as exc:
        raise FreshSearchError(f"OpenAI web search failed: {exc.__class__.__name__}: {exc}") from exc

    results_by_url: dict[str, FreshSearchResult] = {}

    for output_item in response.output:
        if getattr(output_item, "type", "") != "message":
            continue
        for content in getattr(output_item, "content", []):
            if getattr(content, "type", "") != "output_text":
                continue
            text = getattr(content, "text", "") or ""
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
                    snippet = re.sub(r"\s+", " ", text).strip()[:240]
                results_by_url[url] = FreshSearchResult(
                    source_title=(getattr(annotation, "title", "") or "").strip() or _fallback_title_from_url(url),
                    source_url=url,
                    snippet=snippet[:320],
                    searched_on=searched_on,
                    query_text=query_text,
                )

    for output_item in response.output:
        if getattr(output_item, "type", "") != "web_search_call":
            continue
        action = getattr(output_item, "action", None)
        if getattr(action, "type", "") != "search":
            continue
        for source in getattr(action, "sources", []) or []:
            url = (getattr(source, "url", "") or "").strip()
            if not url or url in results_by_url:
                continue
            results_by_url[url] = FreshSearchResult(
                source_title=_fallback_title_from_url(url),
                source_url=url,
                snippet="최신 검색 출처가 확인되었습니다.",
                searched_on=searched_on,
                query_text=query_text,
            )

    results = list(results_by_url.values())
    if not results:
        raise FreshSearchError("OpenAI web search returned no cited sources")
    return results[:limit]
