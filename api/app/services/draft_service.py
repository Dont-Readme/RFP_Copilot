from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.evaluation import EvaluationItem
from app.models.outline import OutlineSection
from app.models.rfp import RfpExtraction, RfpRequirementItem
from app.services.draft_generation_taxonomy import (
    recommended_diagrams_for_pattern,
    recommended_figures_for_pattern,
    recommended_tables_for_pattern,
    summarize_output_guidance,
    summarize_pattern,
)
from app.services.draft_plan_service import PlannedSearchTask
from app.services.llm_service import LLMConfigurationError, LLMResponseError, LLMService
from app.services.prompts import (
    DRAFT_ADAPTIVE_RESEARCH_SYSTEM_PROMPT,
    DRAFT_UNIT_DESIGN_SYSTEM_PROMPT,
    DRAFT_SECTION_SYSTEM_PROMPT,
    build_draft_adaptive_research_user_prompt,
    build_draft_unit_design_user_prompt,
    build_draft_section_user_prompt,
)
from app.services.research_playbooks import (
    build_selected_research_playbook_reference_text,
    select_research_playbook_keys,
)
from app.services.research_orchestrator_service import run_project_research_requests
from app.services.research_service import ResearchRequest, ResearchResult
from app.services.review_item_service import strip_inline_review_items


class DraftGenerationError(RuntimeError):
    pass


class StructuredDraftSection(BaseModel):
    content_md: str = ""
    system_review_items: list[str] = Field(default_factory=list)


class StructuredDraftUnitBlueprint(BaseModel):
    planning_summary: str = ""
    scope_items: list[str] = Field(default_factory=list)
    input_sources: list[str] = Field(default_factory=list)
    process_steps: list[str] = Field(default_factory=list)
    implementation_components: list[str] = Field(default_factory=list)
    operation_controls: list[str] = Field(default_factory=list)
    deliverables: list[str] = Field(default_factory=list)
    differentiation_points: list[str] = Field(default_factory=list)
    recommended_tables: list[str] = Field(default_factory=list)
    recommended_figures: list[str] = Field(default_factory=list)
    recommended_diagrams: list[str] = Field(default_factory=list)
    writing_notes: list[str] = Field(default_factory=list)
    system_review_items: list[str] = Field(default_factory=list)


class StructuredAdaptiveSearchRequest(BaseModel):
    query: str = ""
    purpose: str = ""
    reason: str = ""
    allowed_domains: list[str] = Field(default_factory=list)
    max_results: int = 4


class StructuredAdaptiveSearchPlan(BaseModel):
    needs_additional_search: bool = False
    planning_summary: str = ""
    search_requests: list[StructuredAdaptiveSearchRequest] = Field(default_factory=list)


@dataclass(frozen=True)
class DraftUnitGenerationResult:
    content_md: str
    research_results: list[ResearchResult]


def _rfp_summary(extraction: RfpExtraction) -> str:
    if extraction.project_summary_text:
        return extraction.project_summary_text
    return "구조화된 RFP 요약이 아직 비어 있습니다."


def _requirements_summary(requirements: list[RfpRequirementItem]) -> str:
    if not requirements:
        return "관련 요구사항 없음"
    lines = []
    for requirement in requirements:
        title = (requirement.name or requirement.requirement_no or "요구사항").strip()
        definition = (requirement.definition or "").strip()
        detail = (requirement.details or "").strip()
        lines.append(
            "\n".join(
                [
                    f"- requirement_id={requirement.id}",
                    f"  번호: {requirement.requirement_no or '-'}",
                    f"  제목: {title}",
                    f"  정의: {definition or '-'}",
                    f"  세부 내용:",
                    detail or "  - 세부 내용 확인 필요",
                ]
            )
        )
    return "\n".join(lines)


def _evaluation_summary(evaluation_items: list[EvaluationItem]) -> str:
    if not evaluation_items:
        return "관련 평가항목 없음"
    lines = []
    for item in evaluation_items:
        title = (item.item or "평가항목").strip()
        note = (item.notes or item.score or "").strip()
        lines.append(f"- {title}: {note if note else '평가 포인트 확인 필요'}")
    return "\n".join(lines)


def _company_summary(company_facts: list[str]) -> str:
    if not company_facts:
        return "관련 회사 정보 없음"
    return "\n".join(company_facts)


def _search_summary(search_results: list[ResearchResult]) -> str:
    if not search_results:
        return "최신 검색 결과 없음"
    sections: list[str] = []
    for result in search_results[:6]:
        header = f"[{result.source_stage}/{result.purpose or 'general'}] {result.query}"
        sections.append(f"{header}\n{result.summary.strip()[:900]}")
    return "\n\n".join(sections)


def _paragraph_target(*, depth: int, writing_mode: str) -> str:
    if writing_mode == "execution":
        return "2~4개의 ☐ 메인 블록, 각 블록 아래 2~4개의 ○ 설명, 필요 시 - 상세 항목과 표/도식 포함"
    if writing_mode in {"strategy", "operations"}:
        return "2~3개의 ☐ 메인 블록, 각 블록 아래 2~3개의 ○ 설명, 필요 시 - 상세 항목과 표/도식 포함"
    if depth <= 1:
        return "2~3개의 ☐ 메인 블록, 각 블록 아래 1~3개의 ○ 설명"
    return "1~3개의 ☐ 메인 블록, 각 블록 아래 1~2개의 ○ 설명"


def _normalize_search_requests(tasks: list[PlannedSearchTask]) -> list[ResearchRequest]:
    requests: list[ResearchRequest] = []
    for task in tasks:
        topic = (task.topic or "").strip()
        if not topic:
            continue
        requests.append(
            ResearchRequest(
                query=topic,
                purpose=task.purpose,
                reason=task.reason,
                expected_output=task.expected_output,
                allowed_domains=tuple(task.allowed_domains),
                max_results=max(1, min(task.max_results, 8)),
                source_stage="planned",
            )
        )
    return requests


def _plan_adaptive_research(
    *,
    llm_service: LLMService,
    project_id: int,
    project_name: str,
    section: OutlineSection,
    unit_key: str,
    extraction: RfpExtraction,
    section_goal: str,
    unit_title: str,
    unit_goal: str,
    draft_guidance: str,
    writing_mode: str,
    unit_pattern: str,
    required_aspects: list[str],
    requirements: list[RfpRequirementItem],
    evaluation_items: list[EvaluationItem],
    company_facts: list[str],
    planned_search_results: list[ResearchResult],
) -> list[ResearchRequest]:
    try:
        referenced_playbook_keys = select_research_playbook_keys(
            writing_mode=writing_mode,
            unit_pattern=unit_pattern,
            heading_text=f"{section.display_label} {section.title}".strip(),
        )
        plan = llm_service.parse_chat_completion(
            model=llm_service.settings.openai_model_draft,
            system_prompt=DRAFT_ADAPTIVE_RESEARCH_SYSTEM_PROMPT,
            user_prompt=build_draft_adaptive_research_user_prompt(
                project_name=project_name,
                section_heading=f"{section.display_label} {section.title}".strip(),
                unit_title=unit_title,
                writing_mode=writing_mode,
                unit_pattern=unit_pattern,
                unit_pattern_summary=summarize_pattern(unit_pattern),
                required_aspects=required_aspects,
                section_goal=section_goal,
                unit_goal=unit_goal,
                draft_guidance=draft_guidance,
                rfp_summary=_rfp_summary(extraction),
                requirements_summary=_requirements_summary(requirements),
                evaluation_summary=_evaluation_summary(evaluation_items),
                company_summary=_company_summary(company_facts),
                planned_search_summary=_search_summary(planned_search_results),
                research_playbook_reference=build_selected_research_playbook_reference_text(
                    writing_mode=writing_mode,
                    unit_pattern=unit_pattern,
                    heading_text=f"{section.display_label} {section.title}".strip(),
                ),
            ),
            response_format=StructuredAdaptiveSearchPlan,
            max_completion_tokens=1400,
            trace_project_id=project_id,
            trace_kind="draft.research_planner",
            trace_metadata={
                "outline_section_id": section.id,
                "section_heading": f"{section.display_label} {section.title}".strip(),
                "unit_title": unit_title,
                "writing_mode": writing_mode,
                "unit_pattern": unit_pattern,
                "planned_search_count": len(planned_search_results),
                "referenced_playbook_keys": referenced_playbook_keys,
            },
        )
    except (LLMConfigurationError, LLMResponseError) as exc:
        raise DraftGenerationError(str(exc)) from exc

    if not plan.needs_additional_search:
        return []

    requests: list[ResearchRequest] = []
    seen_queries: set[str] = {item.query.strip().lower() for item in planned_search_results if item.query.strip()}
    for item in plan.search_requests[:2]:
        query = item.query.strip()
        if not query or query.lower() in seen_queries:
            continue
        seen_queries.add(query.lower())
        requests.append(
            ResearchRequest(
                query=query,
                purpose=item.purpose.strip(),
                reason=item.reason.strip() or plan.planning_summary.strip(),
                expected_output="초안 본문 구체화에 바로 사용할 최신 근거 요약",
                allowed_domains=tuple(item.allowed_domains),
                max_results=max(1, min(int(item.max_results or 4), 8)),
                source_stage="adaptive",
                context_summary=f"section={section.display_label} {section.title}".strip(),
            )
        )
    return requests


def _blueprint_summary(blueprint: StructuredDraftUnitBlueprint | None) -> str:
    if blueprint is None:
        return "별도 생성 blueprint 없음"
    sections = []
    if blueprint.planning_summary.strip():
        sections.append(f"계획 요약:\n- {blueprint.planning_summary.strip()}")
    if blueprint.scope_items:
        sections.append("범위:\n" + "\n".join(f"- {item}" for item in blueprint.scope_items))
    if blueprint.input_sources:
        sections.append("입력·데이터원:\n" + "\n".join(f"- {item}" for item in blueprint.input_sources))
    if blueprint.process_steps:
        sections.append("처리·수행 단계:\n" + "\n".join(f"- {item}" for item in blueprint.process_steps))
    if blueprint.implementation_components:
        sections.append("구현 구성요소:\n" + "\n".join(f"- {item}" for item in blueprint.implementation_components))
    if blueprint.operation_controls:
        sections.append("운영·통제:\n" + "\n".join(f"- {item}" for item in blueprint.operation_controls))
    if blueprint.deliverables:
        sections.append("산출물·검증:\n" + "\n".join(f"- {item}" for item in blueprint.deliverables))
    if blueprint.differentiation_points:
        sections.append("차별화 포인트:\n" + "\n".join(f"- {item}" for item in blueprint.differentiation_points))
    if blueprint.recommended_tables:
        sections.append("권장 표:\n" + "\n".join(f"- {item}" for item in blueprint.recommended_tables))
    if blueprint.recommended_figures:
        sections.append("권장 그림:\n" + "\n".join(f"- {item}" for item in blueprint.recommended_figures))
    if blueprint.recommended_diagrams:
        sections.append("권장 도식:\n" + "\n".join(f"- {item}" for item in blueprint.recommended_diagrams))
    if blueprint.writing_notes:
        sections.append("서술 메모:\n" + "\n".join(f"- {item}" for item in blueprint.writing_notes))
    return "\n\n".join(sections) if sections else "별도 생성 blueprint 없음"


def _design_generation_unit(
    *,
    llm_service: LLMService,
    project_id: int,
    project_name: str,
    section: OutlineSection,
    extraction: RfpExtraction,
    section_goal: str,
    unit_title: str,
    unit_goal: str,
    draft_guidance: str,
    writing_mode: str,
    unit_pattern: str,
    required_aspects: list[str],
    requirements: list[RfpRequirementItem],
    evaluation_items: list[EvaluationItem],
    company_facts: list[str],
    search_results: list[ResearchResult],
) -> StructuredDraftUnitBlueprint | None:
    if writing_mode not in {"execution", "strategy"}:
        return None
    try:
        referenced_playbook_keys = select_research_playbook_keys(
            writing_mode=writing_mode,
            unit_pattern=unit_pattern,
            heading_text=f"{section.display_label} {section.title}".strip(),
        )
        return llm_service.parse_chat_completion(
            model=llm_service.settings.openai_model_draft,
            system_prompt=DRAFT_UNIT_DESIGN_SYSTEM_PROMPT,
            user_prompt=build_draft_unit_design_user_prompt(
                project_name=project_name,
                section_heading=f"{section.display_label} {section.title}".strip(),
                unit_title=unit_title,
                writing_mode=writing_mode,
                unit_pattern=unit_pattern,
                unit_pattern_summary=summarize_pattern(unit_pattern),
                output_guidance_summary=summarize_output_guidance(unit_pattern),
                required_aspects=required_aspects,
                section_goal=section_goal,
                unit_goal=unit_goal,
                draft_guidance=draft_guidance,
                rfp_summary=_rfp_summary(extraction),
                requirements_summary=_requirements_summary(requirements),
                evaluation_summary=_evaluation_summary(evaluation_items),
                company_summary=_company_summary(company_facts),
                search_summary=_search_summary(search_results),
                research_playbook_reference=build_selected_research_playbook_reference_text(
                    writing_mode=writing_mode,
                    unit_pattern=unit_pattern,
                    heading_text=f"{section.display_label} {section.title}".strip(),
                ),
            ),
            response_format=StructuredDraftUnitBlueprint,
            max_completion_tokens=3200,
            trace_project_id=project_id,
            trace_kind="draft.designer",
            trace_metadata={
                "outline_section_id": section.id,
                "section_heading": f"{section.display_label} {section.title}".strip(),
                "unit_title": unit_title,
                "writing_mode": writing_mode,
                "unit_pattern": unit_pattern,
                "required_aspect_count": len(required_aspects),
                "requirements_count": len(requirements),
                "referenced_playbook_keys": referenced_playbook_keys,
            },
        )
    except (LLMConfigurationError, LLMResponseError) as exc:
        raise DraftGenerationError(str(exc)) from exc


def generate_section_draft(
    *,
    db: Session,
    llm_service: LLMService,
    project_id: int,
    project_name: str,
    section: OutlineSection,
    unit_key: str,
    extraction: RfpExtraction,
    section_goal: str,
    unit_title: str,
    unit_goal: str,
    draft_guidance: str,
    writing_mode: str,
    unit_pattern: str,
    required_aspects: list[str],
    requirements: list[RfpRequirementItem],
    evaluation_items: list[EvaluationItem],
    company_facts: list[str],
    search_tasks: list[PlannedSearchTask] | None = None,
    search_results: list[ResearchResult] | None = None,
) -> DraftUnitGenerationResult:
    planned_research_results = list(search_results or [])
    if search_tasks:
        planned_outcome = run_project_research_requests(
            db=db,
            project_id=project_id,
            outline_section_id=section.id,
            unit_key=unit_key,
            requests=_normalize_search_requests(search_tasks),
            trace_kind="draft.research.planned",
            trace_metadata={
                "outline_section_id": section.id,
                "section_heading": f"{section.display_label} {section.title}".strip(),
                "unit_title": unit_title,
                "writing_mode": writing_mode,
                "unit_pattern": unit_pattern,
            },
        )
        planned_research_results.extend(list(planned_outcome.results))

    adaptive_search_requests = _plan_adaptive_research(
        llm_service=llm_service,
        project_id=project_id,
        project_name=project_name,
        section=section,
        unit_key=unit_key,
        extraction=extraction,
        section_goal=section_goal,
        unit_title=unit_title,
        unit_goal=unit_goal,
        draft_guidance=draft_guidance,
        writing_mode=writing_mode,
        unit_pattern=unit_pattern,
        required_aspects=required_aspects,
        requirements=requirements,
        evaluation_items=evaluation_items,
        company_facts=company_facts,
        planned_search_results=planned_research_results,
    )
    adaptive_research_results: list[ResearchResult] = []
    if adaptive_search_requests:
        adaptive_outcome = run_project_research_requests(
            db=db,
            project_id=project_id,
            outline_section_id=section.id,
            unit_key=unit_key,
            requests=adaptive_search_requests,
            trace_kind="draft.research.adaptive",
            trace_metadata={
                "outline_section_id": section.id,
                "section_heading": f"{section.display_label} {section.title}".strip(),
                "unit_title": unit_title,
                "writing_mode": writing_mode,
                "unit_pattern": unit_pattern,
            },
        )
        adaptive_research_results.extend(list(adaptive_outcome.results))
    combined_search_results = planned_research_results + adaptive_research_results

    blueprint = _design_generation_unit(
        llm_service=llm_service,
        project_id=project_id,
        project_name=project_name,
        section=section,
        extraction=extraction,
        section_goal=section_goal,
        unit_title=unit_title,
        unit_goal=unit_goal,
        draft_guidance=draft_guidance,
        writing_mode=writing_mode,
        unit_pattern=unit_pattern,
        required_aspects=required_aspects,
        requirements=requirements,
        evaluation_items=evaluation_items,
        company_facts=company_facts,
        search_results=combined_search_results,
    )
    try:
        generated = llm_service.parse_chat_completion(
            model=llm_service.settings.openai_model_draft,
            system_prompt=DRAFT_SECTION_SYSTEM_PROMPT,
            user_prompt=build_draft_section_user_prompt(
                project_name=project_name,
                section_heading=f"{section.display_label} {section.title}".strip(),
                unit_title=unit_title,
                section_depth=section.depth,
                target_length=_paragraph_target(depth=section.depth, writing_mode=writing_mode),
                writing_mode=writing_mode,
                unit_pattern=unit_pattern,
                unit_pattern_summary=summarize_pattern(unit_pattern),
                output_guidance_summary=summarize_output_guidance(unit_pattern),
                required_aspects=required_aspects,
                section_goal=section_goal,
                unit_goal=unit_goal,
                draft_guidance=draft_guidance,
                rfp_summary=_rfp_summary(extraction),
                requirements_summary=_requirements_summary(requirements),
                evaluation_summary=_evaluation_summary(evaluation_items),
                company_summary=_company_summary(company_facts),
                search_summary=_search_summary(combined_search_results),
                blueprint_summary=_blueprint_summary(blueprint),
                suggested_tables=recommended_tables_for_pattern(unit_pattern),
                suggested_figures=recommended_figures_for_pattern(unit_pattern),
                suggested_diagrams=recommended_diagrams_for_pattern(unit_pattern),
            ),
            response_format=StructuredDraftSection,
            max_completion_tokens=5200,
            trace_project_id=project_id,
            trace_kind="draft.writer",
            trace_metadata={
                "outline_section_id": section.id,
                "section_heading": f"{section.display_label} {section.title}".strip(),
                "unit_title": unit_title,
                "writing_mode": writing_mode,
                "unit_pattern": unit_pattern,
                "required_aspect_count": len(required_aspects),
                "requirements_count": len(requirements),
                "evaluation_count": len(evaluation_items),
                "company_fact_count": len(company_facts),
                "search_result_count": len(combined_search_results),
            },
        )
    except (LLMConfigurationError, LLMResponseError) as exc:
        raise DraftGenerationError(str(exc)) from exc

    content_md, _inline_review_items = strip_inline_review_items(generated.content_md.strip())
    return DraftUnitGenerationResult(
        content_md=content_md,
        research_results=combined_search_results,
    )
