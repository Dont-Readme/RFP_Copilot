from __future__ import annotations


def build_web_search_prompt(*, topic: str, searched_on: str, limit: int) -> str:
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


def build_research_request_prompt(
    *,
    query: str,
    purpose: str,
    reason: str,
    expected_output: str,
    searched_on: str,
    max_results: int,
    context_summary: str = "",
) -> str:
    return f"""
오늘 날짜는 {searched_on}입니다.
반드시 web search를 사용해서 아래 조사 요청에 답하세요.

검색 질의:
{query}

검색 목적:
{purpose or "일반 조사"}

검색 이유:
{reason or "-"}

원하는 산출 형태:
{expected_output or "작성에 바로 활용할 수 있는 핵심 사실 요약"}

추가 맥락:
{context_summary or "-"}

지침:
- 최신성 판단은 반드시 위 절대 날짜를 기준으로 하세요.
- 질의와 목적에 직접 필요한 사실만 남기고 주변 잡정보는 제외하세요.
- 한국어로 작성하세요.
- 출처 인용이 붙도록 작성하세요.
- 가능하면 공신력 있는 공공·연구·전문기관 출처를 우선하세요.
- 결과는 최대 {max_results}개의 핵심 bullet로 정리하되, 마지막에 한 줄 요약을 덧붙여도 됩니다.
- 정보가 부족하면 억지로 채우지 말고 부족하다고 분명히 적으세요.
""".strip()
