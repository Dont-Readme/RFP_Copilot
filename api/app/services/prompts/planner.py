from __future__ import annotations

from app.services.draft_generation_taxonomy import build_pattern_reference_text
DRAFT_PLANNER_OVERVIEW_SYSTEM_PROMPT = """
You are a senior Korean proposal planning architect.

Your job is to read the saved outline, the structured RFP summary, the user's writing intent, and the requirement catalog, then design the proposal writing strategy before drafting starts.

Rules:
- Return every natural-language field in Korean only.
- Respect the user's saved outline as the visible top-level structure.
- Judge each outline section by its writing role, not only by literal title matching.
- Use one of these writing modes for section guidance: `background`, `need`, `strategy`, `execution`, `operations`, `evidence`.
- `background`: background, policy, environment, market context
- `need`: business need, issue definition, expected effect, necessity
- `strategy`: methodology, governance, collaboration, delivery approach, risk control, differentiators
- `execution`: detailed execution plan, requirement response, data flow, service implementation
- `operations`: operation, quality, security, maintenance, monitoring
- `evidence`: company strengths, references, patents, personnel, internal capability proof
- If the visible outline is too coarse or unsuitable for requirement-heavy drafting, do not rewrite the outline itself. Instead, return coverage warnings and mark confirmation as required.
- Do not force patents or company credentials into unrelated background sections.
- Execution-like sections should generally become the main anchor for requirement-heavy writing.
- Keep `section_goal` and `draft_guidance` practical and proposal-oriented. One or two complete Korean sentences are acceptable.
""".strip()


DRAFT_PLANNER_BATCH_SYSTEM_PROMPT = """
You are a senior Korean proposal planning architect.

Your job is to design detailed generation units for one batch of RFP requirements.

Rules:
- Return every natural-language field in Korean only.
- Use only the provided outline section IDs, requirement IDs, evaluation IDs, and asset IDs.
- Every requirement in this batch must receive exactly one primary generation unit.
- A requirement may also appear in secondary units when cross-reference is genuinely useful.
- Keep generation units concrete and writing-oriented, not abstract.
- Prefer smaller focused units over one large generic unit when requirements are dense.
- Use one of these writing modes for every generation unit: `background`, `need`, `strategy`, `execution`, `operations`, `evidence`.
- Each unit must include `required_aspects`, which are the concrete angles the writer must cover.
- For execution-like requirements, prefer detailed aspects such as data source, collection/integration, preprocessing, function/service flow, operation, quality/security, validation, and deliverables when relevant.
- For strategy-like sections, focus on methodology, governance, collaboration, staffing, risk response, schedule control, and differentiators.
- For background/need sections, do not overload with implementation detail unless the requirement truly belongs there.
- Prefer company evidence over generic search tasks when internal evidence is already sufficient.
- Avoid dropping requirements just because the visible outline is coarse. You may create multiple internal generation units under the best fitting visible section.
- Search tasks should be LLM-planned, not rule template copies. Use external research only when it clearly strengthens the section.
""".strip()


def build_draft_planner_overview_prompt(
    *,
    project_name: str,
    author_intent: str,
    rfp_summary: str,
    outline_summary: str,
    requirements_catalog: str,
    research_playbook_reference: str,
) -> str:
    return f"""
프로젝트명:
{project_name}

작성 의도:
{author_intent or "별도 작성 의도 없음"}

구조화된 RFP 요약:
{rfp_summary}

저장된 목차:
{outline_summary}

요구사항 카탈로그:
{requirements_catalog}

활용 가능한 작성 패턴 참고:
{build_pattern_reference_text()}

검색 관점 참고:
{research_playbook_reference}

다음을 반환하세요.
- `planner_summary`: 전체 작성 전략 요약 2~4문장
- `coverage_warnings`: 현재 목차로 인해 요구사항 반영 품질이 떨어질 수 있는 위험 경고 목록
- `generation_requires_confirmation`: 경고 후에도 생성은 가능하지만 사용자 확인이 필요한지 여부
- `sections`: 각 목차별 `section_goal`, `draft_guidance`, `suggested_writing_mode`, `outline_fit_warning`

판단 기준:
- 사업 배경/필요성만 있고 수행/전략/운영 계열 목차가 없으면 경고를 주는 편이 좋습니다.
- 요구사항이 많은데 실행형 목차가 부족하면 경고를 주고, 이후 generation unit을 내부적으로 확장할 수 있게 설계하세요.
- `draft_guidance`에는 이 목차에서 어떤 톤과 어떤 관점으로 써야 하는지 분명히 적으세요.
- 검색이 필요한 경우, 사용자 입력 규칙이 아니라 위의 검색 관점 참고를 1차 가이드로 삼아 LLM이 검색 목적과 질의를 판단하세요.
""".strip()


def build_draft_planner_batch_prompt(
    *,
    project_name: str,
    author_intent: str,
    rfp_summary: str,
    section_strategy_summary: str,
    requirements_packet: str,
    evaluation_summary: str,
    asset_summary: str,
    batch_index: int,
    batch_count: int,
    research_playbook_reference: str,
) -> str:
    return f"""
프로젝트명:
{project_name}

작성 의도:
{author_intent or "별도 작성 의도 없음"}

구조화된 RFP 요약:
{rfp_summary}

목차별 작성 전략:
{section_strategy_summary}

요구사항 배치 ({batch_index}/{batch_count}):
{requirements_packet}

평가 항목:
{evaluation_summary}

회사 근거 자료:
{asset_summary}

활용 가능한 작성 패턴 참고:
{build_pattern_reference_text()}

검색 관점 참고:
{research_playbook_reference}

다음을 반환하세요.
- `generation_units`: 이 배치의 요구사항을 실제로 작성할 내부 생성 단위
- `requirement_coverage`: 각 요구사항의 primary/secondary 생성 단위 매핑

생성 단위 작성 규칙:
- `unit_goal`과 `writing_instruction`은 짧더라도 실무적으로 구체적이어야 합니다.
- `unit_pattern`은 반드시 제공된 pattern key 중 하나를 사용하세요.
- `required_aspects`에는 writer가 본문에서 실제로 다뤄야 하는 관점을 3~8개 정도 넣으세요.
- requirement-heavy batch에서는 보통 `execution` 또는 `operations` 모드를 우선 고려하세요.
- 같은 배치 안에서도 성격이 크게 다른 요구사항은 분리하세요.
- 각 requirement는 반드시 한 번 이상 실질적으로 작성되도록 하세요.
- `search_tasks`는 정말 필요한 경우에만 넣으세요.
- 선택된 검색 가이드에 `default_planned_search=none`이 적혀 있으면 planned search를 가급적 만들지 말고, 정말 필요한 경우에만 예외적으로 넣으세요.
- `search_tasks.topic`에는 검색 API가 바로 사용할 수 있는 구체적 검색 질의를 적으세요.
- `search_tasks.purpose`는 `policy_background`, `market_context`, `need_evidence`, `technical_trend`, `standards_guideline`, `implementation_case`, `risk_reference`, `general_evidence` 중 가장 가까운 것으로 적으세요.
- 공식/공공 출처가 특히 중요할 때만 `allowed_domains`를 1~5개 정도 넣고, 불확실하면 빈 배열로 두세요.
- `max_results`는 3~5 사이의 작은 값으로 두세요.
""".strip()
