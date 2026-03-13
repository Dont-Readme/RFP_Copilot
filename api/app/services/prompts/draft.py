from __future__ import annotations

DRAFT_ADAPTIVE_RESEARCH_SYSTEM_PROMPT = """
You decide whether one Korean proposal generation unit needs additional web research before drafting.

Rules:
- Use Korean only for every natural-language field.
- Ask for additional search only when it will materially improve factual grounding, recency, policy context, market context, standards/guidelines, implementation references, or risk evidence.
- Do not request extra search for company-internal facts that should come from uploaded assets.
- Prefer 0~2 focused search requests over many vague requests.
- Search queries must be concrete enough to be sent directly to a web search API.
- Use `allowed_domains` only when official/public domains are clearly appropriate. Otherwise return an empty list.
- If the current planned search results are already sufficient, return no additional search requests.
""".strip()

DRAFT_SECTION_SYSTEM_PROMPT = """
You write one Korean public proposal section.

Rules:
- Use only information supported by the provided RFP summary, related requirements, evaluation items, company facts, and search findings.
- Do not invent numbers, certifications, customers, patents, or performance claims.
- Prefer specific nouns, execution structure, and concrete delivery detail over generic slogans.
- Follow the provided `writing_mode` and `required_aspects` strictly.
- Follow the provided generation blueprint closely and convert it into strong proposal prose instead of ignoring it.
- If the unit is `execution`, write like an actual delivery plan rather than a high-level summary.
- If the unit is `background`, `need`, or `evidence`, stay focused on that purpose and avoid unnecessary implementation detail.
- If the requirements mention data, platform, service, operation, quality, security, deliverables, or verification, explain them concretely when relevant to the current unit.
- When supported by the requirement text, spell out what will be built, what data or input will be used, how it will be processed or integrated, how the service will operate, and how quality or validation will be handled.
- Use hierarchical outline-style drafting by default:
  - `☐` only for major thematic blocks or subhead-like claims
  - `○` under each `☐` for fuller explanatory sentences
  - `-` under each `○` only when detailed execution items, controls, examples, or lists are needed
- Do not flatten the whole section into bullets of the same level.
- Do not use `☐` for every sentence.
- A good default shape is 2~4 main `☐` blocks, each followed by explanatory `○` items, then selective `-` detail where necessary.
- `☐` should feel like a short title or one-sentence claim, not a long paragraph.
- `○` should carry the actual explanation and proposal substance.
- `-` should carry detailed procedures, controls, examples, data items, or step lists.
- `-` may contain multiple connected explanatory sentences when the detail is important; it should not read like a one-word checklist.
- Prefer this hierarchical structure over long essay paragraphs, but keep the text readable and not mechanically repetitive.
- When the pattern or blueprint indicates comparison, definition, 일정, 역할분담, 요구사항 대응, 평가항목 대응, 데이터 항목, 인터페이스, 성능 목표, 테스트 기준, 보안 통제, 산출물, or 연차별 계획, render a Markdown table instead of plain prose.
- When a visual overview would help but an actual image cannot be drawn, insert a figure placeholder like `<그림> 통합 서비스 구성 개념 그림을 넣어주세요`.
- When a flow, architecture, roadmap, or pipeline should be shown, insert a diagram block like:
  `<도식> 데이터 수집부터 서비스 반영까지의 흐름`
  `수집원 -> 연계/수집 -> 정제/표준화 -> 저장 -> 분석/서비스 반영`
- For multi-year or phased work, prefer including a Markdown table and/or `<도식>` that shows year-by-year or phase-by-phase progression.
- Leave `system_review_items` empty unless the response format requires the field.
- Return Markdown only for the section body, without the heading line.
""".strip()

DRAFT_UNIT_DESIGN_SYSTEM_PROMPT = """
You design one Korean public proposal generation unit before prose drafting.

Rules:
- Use only information supported by the provided RFP summary, related requirements, evaluation items, company facts, and search findings.
- Do not invent numbers, certifications, customers, patents, or performance claims.
- Return structured planning output, not polished proposal prose.
- Follow the provided `writing_mode`, `unit_pattern`, and `required_aspects` strictly.
- For `execution` units, design a concrete delivery blueprint that explains what will be built, what data or inputs will be used, how the work will flow, how the service will operate, and how validation/control will be handled.
- For `strategy` units, design a concrete execution strategy covering methodology, governance, collaboration, scheduling/risk control, and differentiators.
- Prefer explicit steps, entities, controls, and deliverables over generic abstract language.
- Organize the blueprint so the final prose can become a hierarchy of a few major `☐` blocks, several `○` explanations under each, and selective `-` detail lines.
- Recommend helpful tables, figures, and diagrams when they would materially improve clarity.
- Leave `system_review_items` empty unless the response format requires the field.
""".strip()

CHAT_EDIT_SYSTEM_PROMPT = """
You are editing a Korean proposal draft with the user through a chat interface.

Rules:
- Respect the user's edit request exactly.
- Use only information supported by the draft and structured RFP summary.
- If the user selected text, return replacement text only for the selected span, not the full draft.
- If no text is selected, provide guidance only and leave `suggestion_text` empty with `apply_mode=advice_only`.
- Do not invent numbers, certifications, customers, or performance claims.
- If a requested fact is missing, mention that clearly in `assistant_reply`. Do not include `[확인 필요(시스템)]` in `assistant_reply` or `suggestion_text`.
- Keep the assistant reply concise and practical.
- Leave `system_review_items` empty.
""".strip()


def build_draft_adaptive_research_user_prompt(
    *,
    project_name: str,
    section_heading: str,
    unit_title: str,
    writing_mode: str,
    unit_pattern: str,
    unit_pattern_summary: str,
    required_aspects: list[str],
    section_goal: str,
    unit_goal: str,
    draft_guidance: str,
    rfp_summary: str,
    requirements_summary: str,
    evaluation_summary: str,
    company_summary: str,
    planned_search_summary: str,
    research_playbook_reference: str,
) -> str:
    return f"""
Project name: {project_name}
Visible section heading: {section_heading}
Generation unit title: {unit_title}
Writing mode: {writing_mode}
Unit pattern: {unit_pattern}
Pattern guidance: {unit_pattern_summary or "-"}

Required aspects:
{chr(10).join(f"- {item}" for item in required_aspects) if required_aspects else "- planner specified no extra aspects"}

Section goal:
{section_goal}

Generation unit goal:
{unit_goal}

Draft guidance:
{draft_guidance}

Structured RFP summary:
{rfp_summary}

Related requirements:
{requirements_summary}

Related evaluation items:
{evaluation_summary}

Company facts:
{company_summary}

Current planned search findings:
{planned_search_summary}

Research playbook reference:
{research_playbook_reference}

판단 기준:
- 외부 검색은 최신 정책, 시장 현황, 통계 근거, 기술 동향, 표준/가이드라인, 유사 추진 사례, 리스크 대응 근거가 필요할 때만 요청하세요.
- 이미 계획 검색 결과가 충분하면 추가 검색을 만들지 마세요.
- 검색 관점 참고서는 1차 가이드일 뿐이며, 현재 unit의 요구사항과 작성 목적에 맞춰 질의를 스스로 구체화하세요.
- 선택된 검색 가이드에 `adaptive_search_allowed=no`가 적혀 있으면 추가 검색을 만들지 마세요. 정말 예외적인 경우에만 필요성을 강하게 설명해야 합니다.
- 각 검색 요청은 `query`, `purpose`, `reason`, `allowed_domains`, `max_results`를 채우세요.
- `purpose`는 검색 결과를 writer가 어디에 쓸지 드러나게 짧게 적으세요.
""".strip()

def build_draft_section_user_prompt(
    *,
    project_name: str,
    section_heading: str,
    unit_title: str,
    section_depth: int,
    target_length: str,
    writing_mode: str,
    unit_pattern: str,
    unit_pattern_summary: str,
    output_guidance_summary: str,
    required_aspects: list[str],
    section_goal: str,
    unit_goal: str,
    draft_guidance: str,
    rfp_summary: str,
    requirements_summary: str,
    evaluation_summary: str,
    company_summary: str,
    search_summary: str,
    blueprint_summary: str,
    suggested_tables: list[str],
    suggested_figures: list[str],
    suggested_diagrams: list[str],
) -> str:
    return f"""
Project name: {project_name}
Visible section heading: {section_heading}
Generation unit title: {unit_title}
Section depth: {section_depth}
Target length: {target_length}
Writing mode: {writing_mode}
Unit pattern: {unit_pattern}
Pattern guidance: {unit_pattern_summary or "-"}
Pattern output guidance:
{output_guidance_summary or "-"}
Required aspects:
{chr(10).join(f"- {item}" for item in required_aspects) if required_aspects else "- planner specified no extra aspects"}

Section goal:
{section_goal}

Generation unit goal:
{unit_goal}

Draft guidance:
{draft_guidance}

Structured RFP summary:
{rfp_summary}

Related requirements:
{requirements_summary}

Related evaluation items:
{evaluation_summary}

Company facts:
{company_summary}

Recent search findings:
{search_summary}

Generation blueprint:
{blueprint_summary}

Write the section body only.
Quality expectations:
- Avoid generic mission-statement prose unless the current mode is `background` or `need`.
- If the current mode is `execution`, prefer a requirement-by-requirement delivery narrative with concrete implementation flow.
- If a requirement concerns data, cover the data scope, source or collection path, preprocessing or standardization, service/application use, and operation or validation when the evidence supports it.
- If a requirement concerns operations, quality, or security, describe governance and control mechanisms concretely.
- Default to outline-style Korean proposal drafting using `☐`, `○`, `-`.
- Use `☐` as a short title-like sentence for the biggest response units only.
- Under each `☐`, use `○` for fuller explanation paragraphs or proposal statements.
- Under each `○`, use `-` only for finer detail such as data items, 단계별 조치, 통제 방안, examples, or deliverables.
- Let `-` explain the detail enough for the proposal to feel concrete; it may be several sentences when needed, as long as it stays under the relevant `○`.
- Do not make every sentence a `☐`.
- Prefer a shape like:
  `☐ 데이터 수집 체계 구축`
  `○ 기관 내부 시스템, 외부 공공데이터, 현장 수집정보를 연계해 서비스 운영에 필요한 기준 데이터를 확보한다.`
  `- 내부 행정시스템 데이터는 배치 또는 API 방식으로 수집하고, 수집 주기와 책임 주체를 구분해 운영 안정성을 확보한다. 연계 오류가 발생하면 재수집 절차와 검증 로그를 함께 관리한다.`
  `- 외부 공공데이터는 표준 코드 기준으로 정규화하고, 서비스 화면과 분석 기능에서 동일한 기준값을 활용할 수 있도록 공통 참조 체계로 관리한다.`
- Prefer tables when the content is definitional, comparative, phased, or list-heavy.
- Suggested tables:
{chr(10).join(f"- {item}" for item in suggested_tables) if suggested_tables else "- 필요 시만 사용"}
- Suggested figures:
{chr(10).join(f"- {item}" for item in suggested_figures) if suggested_figures else "- 필요 시만 사용"}
- Suggested diagrams:
{chr(10).join(f"- {item}" for item in suggested_diagrams) if suggested_diagrams else "- 필요 시만 사용"}
- Markdown tables are allowed and preferred for structured content.
- Figure placeholders must use the form `<그림> ...`.
- Diagram placeholders must use the form `<도식> ...` followed by `->` based text flow.

Leave `system_review_items` empty.
""".strip()


def build_draft_unit_design_user_prompt(
    *,
    project_name: str,
    section_heading: str,
    unit_title: str,
    writing_mode: str,
    unit_pattern: str,
    unit_pattern_summary: str,
    output_guidance_summary: str,
    required_aspects: list[str],
    section_goal: str,
    unit_goal: str,
    draft_guidance: str,
    rfp_summary: str,
    requirements_summary: str,
    evaluation_summary: str,
    company_summary: str,
    search_summary: str,
    research_playbook_reference: str,
) -> str:
    return f"""
Project name: {project_name}
Visible section heading: {section_heading}
Generation unit title: {unit_title}
Writing mode: {writing_mode}
Unit pattern: {unit_pattern}
Pattern guidance: {unit_pattern_summary or "-"}
Pattern output guidance:
{output_guidance_summary or "-"}
Required aspects:
{chr(10).join(f"- {item}" for item in required_aspects) if required_aspects else "- planner specified no extra aspects"}

Section goal:
{section_goal}

Generation unit goal:
{unit_goal}

Draft guidance:
{draft_guidance}

Structured RFP summary:
{rfp_summary}

Related requirements:
{requirements_summary}

Related evaluation items:
{evaluation_summary}

Company facts:
{company_summary}

Recent search findings:
{search_summary}

Research playbook guidance:
{research_playbook_reference}

Return a concrete generation blueprint.
For `execution`, be explicit about scope, inputs or data sources, process flow, integration or implementation steps, operational controls, deliverables, and differentiators when relevant.
For `strategy`, be explicit about methodology, governance, collaboration, scheduling, risk response, and execution differentiators.
- Also recommend when a Markdown table, `<그림>`, or `<도식>` would improve clarity.
""".strip()


def build_chat_edit_user_prompt(
    *,
    project_name: str,
    draft_title: str,
    rfp_summary: str,
    recent_chat_history: str,
    draft_excerpt: str,
    selected_text: str,
    user_request: str,
) -> str:
    return f"""
Project name: {project_name}
Draft title: {draft_title}

Structured RFP summary:
{rfp_summary}

Recent chat history:
{recent_chat_history}

Draft excerpt:
{draft_excerpt}

Selected text:
{selected_text}

User request:
{user_request}

Return:
- `assistant_reply`: what you tell the user
- `suggestion_text`: replacement text for the selected span, or empty if no selection
- `apply_mode`: `replace_selection` or `advice_only`
- `diff_hint`: short note about what changed
- `system_review_items`: always return an empty list
""".strip()
