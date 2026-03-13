from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re

from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.models.evaluation import EvaluationItem
from app.models.library import LibraryAsset
from app.models.outline import OutlineSection
from app.models.rfp import RfpExtraction, RfpRequirementItem
from app.services.draft_generation_taxonomy import (
    default_required_aspects_for_pattern,
    infer_unit_pattern,
    normalize_writing_mode,
)
from app.services.draft_plan_service import (
    DraftGenerationUnit,
    DraftPlanResult,
    DraftRequirementCoverage,
    DraftSectionPlan,
    PlannedSearchTask,
    _company_facts_from_assets,
    _playbook_for_heading,
    build_heading_text,
)
from app.services.draft_service import DraftGenerationError
from app.services.llm_service import LLMConfigurationError, LLMResponseError, LLMService
from app.services.prompts import (
    DRAFT_PLANNER_BATCH_SYSTEM_PROMPT,
    DRAFT_PLANNER_OVERVIEW_SYSTEM_PROMPT,
    build_draft_planner_batch_prompt,
    build_draft_planner_overview_prompt,
)
from app.services.research_playbooks import (
    build_selected_research_playbook_reference_text_for_headings,
    select_research_playbook_keys_for_headings,
)

DELIVERY_WRITING_MODES = {"execution", "operations", "strategy"}
BACKGROUND_LIKE_MODES = {"background", "need", "evidence"}


class PlannerSearchTaskOutput(BaseModel):
    topic: str = ""
    purpose: str = ""
    reason: str = ""
    freshness_required: bool = True
    expected_output: str = ""
    allowed_domains: list[str] = Field(default_factory=list)
    max_results: int = 4


class PlannerSectionOverviewOutput(BaseModel):
    outline_section_id: int
    section_goal: str = ""
    draft_guidance: str = ""
    suggested_writing_mode: str = ""
    outline_fit_warning: str = ""


class PlannerGenerationUnitOutput(BaseModel):
    unit_key: str = ""
    outline_section_id: int
    unit_title: str = ""
    unit_goal: str = ""
    writing_instruction: str = ""
    writing_mode: str = ""
    unit_pattern: str = ""
    required_aspects: list[str] = Field(default_factory=list)
    primary_requirement_ids: list[int] = Field(default_factory=list)
    secondary_requirement_ids: list[int] = Field(default_factory=list)
    evaluation_item_ids: list[int] = Field(default_factory=list)
    asset_ids: list[int] = Field(default_factory=list)
    search_tasks: list[PlannerSearchTaskOutput] = Field(default_factory=list)
    outline_fit_warning: str = ""


class PlannerRequirementCoverageOutput(BaseModel):
    requirement_id: int
    primary_unit_key: str = ""
    secondary_unit_keys: list[str] = Field(default_factory=list)
    rationale: str = ""


class StructuredDraftPlannerOverviewResult(BaseModel):
    planner_summary: str = ""
    coverage_warnings: list[str] = Field(default_factory=list)
    generation_requires_confirmation: bool = False
    sections: list[PlannerSectionOverviewOutput] = Field(default_factory=list)


class StructuredDraftPlannerBatchResult(BaseModel):
    generation_units: list[PlannerGenerationUnitOutput] = Field(default_factory=list)
    requirement_coverage: list[PlannerRequirementCoverageOutput] = Field(default_factory=list)


PLANNER_CACHE_VERSION = "planner_quality_v4_backend_research_guides"
MAX_PLANNER_BATCH_SPLIT_DEPTH = 8
MAX_PLANNER_BATCH_COUNT = 48
MAX_GENERATION_UNITS = 160
MAX_UNIT_KEY_COLLISION_ATTEMPTS = 200
MAX_FALLBACK_BUNDLES = 80


def _planner_cache_path(project_id: int) -> Path:
    settings = get_settings()
    cache_dir = settings.app_data_dir / "planner_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"project_{project_id}.json"


def _planner_cache_fingerprint(
    *,
    project_name: str,
    author_intent: str,
    sections: list[OutlineSection],
    extraction: RfpExtraction,
    requirements: list[RfpRequirementItem],
    evaluation_items: list[EvaluationItem],
    assets: list[LibraryAsset],
    asset_text_index: dict[int, list[str]] | None = None,
) -> str:
    payload = {
        "planner_cache_version": PLANNER_CACHE_VERSION,
        "project_name": project_name,
        "author_intent": author_intent,
        "extraction": {
            "project_summary_text": extraction.project_summary_text,
            "raw_text": extraction.raw_text[:4000],
            "updated_at": getattr(extraction, "updated_at", None).isoformat()
            if getattr(extraction, "updated_at", None) is not None
            else "",
        },
        "sections": [
            {
                "id": section.id,
                "depth": section.depth,
                "display_label": section.display_label,
                "title": section.title,
                "needs_search": bool(section.needs_search),
                "updated_at": section.updated_at.isoformat(),
            }
            for section in sections
        ],
        "requirements": [
            {
                "id": requirement.id,
                "sort_order": requirement.sort_order,
                "requirement_no": requirement.requirement_no,
                "name": requirement.name,
                "definition": requirement.definition,
                "details": requirement.details,
            }
            for requirement in requirements
        ],
        "evaluation_items": [
            {
                "id": item.id,
                "item": item.item,
                "score": item.score,
                "notes": item.notes,
            }
            for item in evaluation_items
        ],
        "assets": [
            {
                "id": asset.id,
                "category": asset.category,
                "title": asset.title,
                "snippets": [snippet[:220] for snippet in (asset_text_index or {}).get(asset.id, [])[:2]],
            }
            for asset in assets
        ],
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _load_cached_planner_result(
    *,
    project_id: int,
    fingerprint: str,
) -> DraftPlanResult | None:
    cache_path = _planner_cache_path(project_id)
    if not cache_path.exists():
        return None
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if payload.get("fingerprint") != fingerprint:
        return None
    try:
        plan_payload = payload.get("plan_result", {})
        sections: list[DraftSectionPlan] = []
        return DraftPlanResult(
            ready=bool(plan_payload.get("ready", False)),
            warnings=list(plan_payload.get("warnings", [])),
            sections=sections,
        )
    except Exception:
        return None


def _save_cached_planner_result(
    *,
    project_id: int,
    fingerprint: str,
    plan_result: DraftPlanResult,
) -> None:
    cache_path = _planner_cache_path(project_id)
    payload = {
        "fingerprint": fingerprint,
        "plan_result": {
            "ready": plan_result.ready,
            "warnings": plan_result.warnings,
            "author_intent": plan_result.author_intent,
            "planner_summary": plan_result.planner_summary,
            "planner_mode": plan_result.planner_mode,
            "generation_requires_confirmation": plan_result.generation_requires_confirmation,
            "coverage_warnings": plan_result.coverage_warnings,
            "sections": [
                {
                    "section_id": item.section.id,
                    "heading_text": item.heading_text,
                    "heading_path": item.heading_path,
                    "section_goal": item.section_goal,
                    "assigned_requirement_ids": [requirement.id for requirement in item.assigned_requirements],
                    "assigned_evaluation_ids": [evaluation.id for evaluation in item.assigned_evaluation_items],
                    "assigned_asset_ids": [asset.id for asset in item.assigned_assets],
                    "assigned_company_facts": item.assigned_company_facts,
                    "draft_guidance": item.draft_guidance,
                    "search_tasks": [
                        {
                            "topic": task.topic,
                            "purpose": task.purpose,
                            "reason": task.reason,
                            "freshness_required": task.freshness_required,
                            "expected_output": task.expected_output,
                            "allowed_domains": task.allowed_domains,
                            "max_results": task.max_results,
                        }
                        for task in item.search_tasks
                    ],
                    "status": item.status,
                }
                for item in plan_result.sections
            ],
            "generation_units": [
                {
                    "unit_key": unit.unit_key,
                    "outline_section_id": unit.outline_section_id,
                    "unit_title": unit.unit_title,
                    "section_heading_text": unit.section_heading_text,
                    "section_goal": unit.section_goal,
                    "unit_goal": unit.unit_goal,
                    "writing_instruction": unit.writing_instruction,
                    "writing_mode": unit.writing_mode,
                    "unit_pattern": unit.unit_pattern,
                    "required_aspects": unit.required_aspects,
                    "primary_requirement_ids": unit.primary_requirement_ids,
                    "secondary_requirement_ids": unit.secondary_requirement_ids,
                    "evaluation_item_ids": unit.evaluation_item_ids,
                    "asset_ids": unit.asset_ids,
                    "company_facts": unit.company_facts,
                    "search_tasks": [
                        {
                            "topic": task.topic,
                            "purpose": task.purpose,
                            "reason": task.reason,
                            "freshness_required": task.freshness_required,
                            "expected_output": task.expected_output,
                            "allowed_domains": task.allowed_domains,
                            "max_results": task.max_results,
                        }
                        for task in unit.search_tasks
                    ],
                    "outline_fit_warning": unit.outline_fit_warning,
                }
                for unit in plan_result.generation_units
            ],
            "requirement_coverage": [
                {
                    "requirement_id": item.requirement_id,
                    "primary_unit_key": item.primary_unit_key,
                    "primary_outline_section_id": item.primary_outline_section_id,
                    "secondary_unit_keys": item.secondary_unit_keys,
                    "rationale": item.rationale,
                }
                for item in plan_result.requirement_coverage
            ],
        },
    }
    cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _restore_cached_planner_result(
    *,
    project_id: int,
    fingerprint: str,
    sections: list[OutlineSection],
    requirements: list[RfpRequirementItem],
    evaluation_items: list[EvaluationItem],
    assets: list[LibraryAsset],
) -> DraftPlanResult | None:
    cache_path = _planner_cache_path(project_id)
    if not cache_path.exists():
        return None
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if payload.get("fingerprint") != fingerprint:
        return None

    plan_payload = payload.get("plan_result", {})
    section_by_id = {section.id: section for section in sections}
    requirement_by_id = {item.id: item for item in requirements}
    evaluation_by_id = {item.id: item for item in evaluation_items}
    asset_by_id = {item.id: item for item in assets}

    try:
        restored_sections = [
            DraftSectionPlan(
                section=section_by_id[item["section_id"]],
                heading_text=item["heading_text"],
                heading_path=item["heading_path"],
                section_goal=item["section_goal"],
                assigned_requirements=[
                    requirement_by_id[requirement_id]
                    for requirement_id in item.get("assigned_requirement_ids", [])
                    if requirement_id in requirement_by_id
                ],
                assigned_evaluation_items=[
                    evaluation_by_id[evaluation_id]
                    for evaluation_id in item.get("assigned_evaluation_ids", [])
                    if evaluation_id in evaluation_by_id
                ],
                assigned_assets=[
                    asset_by_id[asset_id]
                    for asset_id in item.get("assigned_asset_ids", [])
                    if asset_id in asset_by_id
                ],
                assigned_company_facts=item.get("assigned_company_facts", []),
                draft_guidance=item.get("draft_guidance", ""),
                search_tasks=[
                    PlannedSearchTask(
                        topic=task.get("topic", ""),
                        purpose=task.get("purpose", ""),
                        reason=task.get("reason", ""),
                        freshness_required=bool(task.get("freshness_required", True)),
                        expected_output=task.get("expected_output", ""),
                        allowed_domains=list(task.get("allowed_domains", [])),
                        max_results=int(task.get("max_results", 4) or 4),
                    )
                    for task in item.get("search_tasks", [])
                ],
                status=item.get("status", "planned"),
            )
            for item in plan_payload.get("sections", [])
            if item.get("section_id") in section_by_id
        ]
        restored_units = [
            DraftGenerationUnit(
                unit_key=item.get("unit_key", ""),
                outline_section_id=item["outline_section_id"],
                unit_title=item.get("unit_title", ""),
                section_heading_text=item.get("section_heading_text", ""),
                section_goal=item.get("section_goal", ""),
                unit_goal=item.get("unit_goal", ""),
                writing_instruction=item.get("writing_instruction", ""),
                writing_mode=item.get("writing_mode", "execution"),
                unit_pattern=item.get("unit_pattern", "functional_workflow"),
                required_aspects=item.get("required_aspects", []),
                primary_requirement_ids=item.get("primary_requirement_ids", []),
                secondary_requirement_ids=item.get("secondary_requirement_ids", []),
                evaluation_item_ids=item.get("evaluation_item_ids", []),
                asset_ids=item.get("asset_ids", []),
                company_facts=item.get("company_facts", []),
                search_tasks=[
                    PlannedSearchTask(
                        topic=task.get("topic", ""),
                        purpose=task.get("purpose", ""),
                        reason=task.get("reason", ""),
                        freshness_required=bool(task.get("freshness_required", True)),
                        expected_output=task.get("expected_output", ""),
                        allowed_domains=list(task.get("allowed_domains", [])),
                        max_results=int(task.get("max_results", 4) or 4),
                    )
                    for task in item.get("search_tasks", [])
                ],
                outline_fit_warning=item.get("outline_fit_warning", ""),
            )
            for item in plan_payload.get("generation_units", [])
        ]
        restored_coverage = [
            DraftRequirementCoverage(
                requirement_id=item["requirement_id"],
                primary_unit_key=item.get("primary_unit_key", ""),
                primary_outline_section_id=item.get("primary_outline_section_id", 0),
                secondary_unit_keys=item.get("secondary_unit_keys", []),
                rationale=item.get("rationale", ""),
            )
            for item in plan_payload.get("requirement_coverage", [])
            if item.get("requirement_id") in requirement_by_id
        ]
        return DraftPlanResult(
            ready=bool(plan_payload.get("ready", True)),
            warnings=list(plan_payload.get("warnings", [])),
            sections=restored_sections,
            author_intent=plan_payload.get("author_intent", ""),
            planner_summary=plan_payload.get("planner_summary", ""),
            planner_mode=plan_payload.get("planner_mode", "ai_v2"),
            generation_units=restored_units,
            requirement_coverage=restored_coverage,
            coverage_warnings=list(plan_payload.get("coverage_warnings", [])),
            generation_requires_confirmation=bool(
                plan_payload.get("generation_requires_confirmation", False)
            ),
        )
    except Exception:
        return None


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text).strip().lower()


def _normalize_planner_summary(summary: str) -> str:
    cleaned = re.sub(r"\s+", " ", (summary or "").strip())
    if not cleaned:
        return "목차와 요구사항을 기준으로 생성 단위와 커버리지를 구성했습니다."
    hangul_count = len(re.findall(r"[가-힣]", cleaned))
    latin_count = len(re.findall(r"[A-Za-z]", cleaned))
    if latin_count > hangul_count * 2 and hangul_count < 8:
        return "목차와 요구사항을 기준으로 생성 단위와 커버리지를 구성했습니다."
    return cleaned


def _heading_paths(sections: list[OutlineSection]) -> dict[int, list[str]]:
    paths: dict[int, list[str]] = {}
    stack: list[str] = []
    for section in sections:
        depth = max(1, section.depth)
        stack = stack[: depth - 1]
        stack.append(build_heading_text(section))
        paths[section.id] = stack.copy()
    return paths


def _rfp_summary_text(extraction: RfpExtraction) -> str:
    if extraction.project_summary_text.strip():
        return extraction.project_summary_text.strip()[:5000]
    return extraction.raw_text.strip()[:5000] or "RFP summary unavailable"


def _outline_summary(sections: list[OutlineSection]) -> str:
    if not sections:
        return "저장된 목차 없음"
    lines = []
    for section in sections:
        heading = build_heading_text(section)
        lines.append(
            f"- outline_section_id={section.id} | depth={section.depth} | heading={heading} | needs_search={bool(section.needs_search)}"
        )
    return "\n".join(lines)


def _requirements_catalog_for_overview(requirements: list[RfpRequirementItem]) -> str:
    if not requirements:
        return "요구사항 없음"
    lines = []
    for requirement in sorted(requirements, key=lambda item: (item.sort_order, item.id)):
        label = (requirement.name or requirement.requirement_no or "요구사항").strip()
        summary = (requirement.definition or requirement.details or "").strip()
        summary = re.sub(r"\s+", " ", summary)
        lines.append(
            f"- requirement_id={requirement.id} | no={requirement.requirement_no or '-'} | title={label} | summary={summary[:240] if summary else '-'}"
        )
    return "\n".join(lines)


def _requirements_packet(requirements: list[RfpRequirementItem]) -> str:
    if not requirements:
        return "요구사항 없음"
    packets = []
    for requirement in sorted(requirements, key=lambda item: (item.sort_order, item.id)):
        packets.append(
            "\n".join(
                [
                    f"[requirement_id={requirement.id}]",
                    f"번호: {requirement.requirement_no or '-'}",
                    f"제목: {(requirement.name or requirement.requirement_no or '요구사항').strip()}",
                    f"정의: {(requirement.definition or '-').strip()}",
                    "세부 내용:",
                    (requirement.details or "-").strip(),
                ]
            )
        )
    return "\n\n".join(packets)


def _evaluation_summary(evaluation_items: list[EvaluationItem]) -> str:
    if not evaluation_items:
        return "평가항목 없음"
    lines = []
    for item in evaluation_items:
        detail = (item.notes or item.score or "").strip()
        lines.append(
            f"- evaluation_item_id={item.id} | item={item.item or '-'} | detail={detail if detail else '-'}"
        )
    return "\n".join(lines)


def _asset_summary(
    assets: list[LibraryAsset],
    asset_text_index: dict[int, list[str]] | None = None,
) -> str:
    if not assets:
        return "회사 자료 없음"
    lines = []
    for asset in assets:
        snippets = [
            re.sub(r"\s+", " ", snippet).strip()
            for snippet in (asset_text_index or {}).get(asset.id, [])
            if snippet.strip()
        ]
        preview = " | ".join(snippet[:220] for snippet in snippets[:2])
        lines.append(
            f"- asset_id={asset.id} | category={asset.category} | title={asset.title} | snippet={preview or '-'}"
        )
    return "\n".join(lines)


def _best_execution_section(sections: list[OutlineSection]) -> OutlineSection:
    keywords = (
        ("사업수행", 10),
        ("수행내용", 10),
        ("제안내용", 9),
        ("수행방안", 9),
        ("구축방안", 9),
        ("추진계획", 8),
        ("사업내용", 8),
        ("수행", 5),
        ("내용", 4),
        ("방안", 4),
        ("구축", 4),
        ("서비스", 3),
        ("기능", 3),
        ("전략", 2),
    )
    penalties = ("배경", "회사소개", "일반현황", "개요", "실적", "레퍼런스")

    def score(section: OutlineSection) -> tuple[int, int, int]:
        heading = _compact(build_heading_text(section))
        total = 0
        for keyword, weight in keywords:
            if keyword in heading:
                total += weight
        if any(keyword in heading for keyword in penalties):
            total -= 5
        return (total, -section.depth, -section.id)

    return max(sections, key=score)


def _dedupe_search_tasks(tasks: list[PlannedSearchTask]) -> list[PlannedSearchTask]:
    deduped: list[PlannedSearchTask] = []
    seen: set[tuple[str, str, tuple[str, ...]]] = set()
    for task in tasks:
        topic = task.topic.strip()
        if not topic:
            continue
        key = (
            topic,
            task.purpose.strip(),
            tuple(task.allowed_domains),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(task)
    return deduped


def _normalize_search_tasks(outputs: list[PlannerSearchTaskOutput]) -> list[PlannedSearchTask]:
    tasks = [
        PlannedSearchTask(
            topic=item.topic.strip(),
            purpose=item.purpose.strip(),
            reason=item.reason.strip(),
            freshness_required=item.freshness_required,
            expected_output=item.expected_output.strip(),
            allowed_domains=list(dict.fromkeys([domain.strip() for domain in item.allowed_domains if domain.strip()]))[:8],
            max_results=max(1, min(int(item.max_results or 4), 8)),
        )
        for item in outputs
        if item.topic.strip()
    ]
    return _dedupe_search_tasks(tasks)[:6]


def _clean_unit_key(raw_key: str, *, outline_section_id: int, unit_index: int) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_-]+", "-", raw_key.strip()).strip("-").lower()
    if normalized:
        return normalized
    return f"section-{outline_section_id}-unit-{unit_index}"


def _requirement_family_key(requirement: RfpRequirementItem) -> str:
    for value in ((requirement.requirement_no or "").strip(), (requirement.name or "").strip()):
        if not value:
            continue
        if "-" in value:
            prefix = value.split("-", 1)[0].strip()
            if prefix:
                return prefix
        tokens = re.findall(r"[A-Za-z0-9가-힣]+", value)
        if tokens:
            return tokens[0]
    return "요구사항"


def _fallback_unit_title(requirements: list[RfpRequirementItem], index: int) -> str:
    if not requirements:
        return f"생성 단위 {index}"
    family = _requirement_family_key(requirements[0])
    if len(requirements) == 1:
        label = (requirements[0].name or requirements[0].requirement_no or family).strip()
        return f"{label} 대응"
    return f"{family} 요구사항 대응 {index}"


def _unique_ids(values: list[int]) -> list[int]:
    return list(dict.fromkeys(values))


def _normalize_required_aspects(
    *,
    raw_aspects: list[str],
    writing_mode: str,
    unit_pattern: str,
    requirements: list[RfpRequirementItem],
    heading_text: str,
) -> list[str]:
    cleaned = [re.sub(r"\s+", " ", item).strip() for item in raw_aspects if item and item.strip()]
    if cleaned:
        return list(dict.fromkeys(cleaned))[:10]
    return default_required_aspects_for_pattern(
        infer_unit_pattern(
            writing_mode=writing_mode,
            heading_text=heading_text,
            requirements=requirements,
            requested_pattern=unit_pattern,
        )
    )


def _build_section_plan_lookup(
    ai_sections: list[PlannerSectionOverviewOutput],
    sections: list[OutlineSection],
) -> tuple[dict[int, str], dict[int, str], dict[int, str], dict[int, str]]:
    section_goal_by_id: dict[int, str] = {}
    guidance_by_id: dict[int, str] = {}
    mode_by_id: dict[int, str] = {}
    warning_by_id: dict[int, str] = {}

    for section in sections:
        heading_text = build_heading_text(section)
        fallback_goal, fallback_guidance = _playbook_for_heading(heading_text)
        section_goal_by_id[section.id] = fallback_goal
        guidance_by_id[section.id] = fallback_guidance
        mode_by_id[section.id] = normalize_writing_mode("", heading_text=heading_text)
        warning_by_id[section.id] = ""

    for item in ai_sections:
        if item.outline_section_id not in section_goal_by_id:
            continue
        if item.section_goal.strip():
            section_goal_by_id[item.outline_section_id] = item.section_goal.strip()
        if item.draft_guidance.strip():
            guidance_by_id[item.outline_section_id] = item.draft_guidance.strip()
        mode_by_id[item.outline_section_id] = normalize_writing_mode(
            item.suggested_writing_mode,
            heading_text=build_heading_text(next(section for section in sections if section.id == item.outline_section_id)),
        )
        warning_by_id[item.outline_section_id] = item.outline_fit_warning.strip()
    return section_goal_by_id, guidance_by_id, mode_by_id, warning_by_id


def _section_strategy_summary(
    sections: list[OutlineSection],
    *,
    section_goal_by_id: dict[int, str],
    guidance_by_id: dict[int, str],
    mode_by_id: dict[int, str],
    warning_by_id: dict[int, str],
) -> str:
    lines = []
    for section in sections:
        lines.append(
            "\n".join(
                [
                    f"[outline_section_id={section.id}]",
                    f"heading={build_heading_text(section)}",
                    f"writing_mode={mode_by_id.get(section.id, 'execution')}",
                    f"section_goal={section_goal_by_id.get(section.id, '')}",
                    f"draft_guidance={guidance_by_id.get(section.id, '')}",
                    f"outline_fit_warning={warning_by_id.get(section.id, '-') or '-'}",
                ]
            )
        )
    return "\n\n".join(lines)


def _requirement_packet_length(requirement: RfpRequirementItem) -> int:
    return len(_requirements_packet([requirement]))


def _build_requirement_batches(
    requirements: list[RfpRequirementItem],
    *,
    max_items: int = 4,
    max_chars: int = 5200,
) -> list[list[RfpRequirementItem]]:
    if not requirements:
        return []
    grouped: dict[str, list[RfpRequirementItem]] = defaultdict(list)
    for requirement in sorted(requirements, key=lambda item: (item.sort_order, item.id)):
        grouped[_requirement_family_key(requirement)].append(requirement)

    batches: list[list[RfpRequirementItem]] = []
    for family_key in sorted(grouped.keys()):
        current: list[RfpRequirementItem] = []
        current_chars = 0
        for requirement in grouped[family_key]:
            estimate = _requirement_packet_length(requirement)
            if current and (len(current) >= max_items or current_chars + estimate > max_chars):
                batches.append(current)
                current = []
                current_chars = 0
            current.append(requirement)
            current_chars += estimate
        if current:
            batches.append(current)
    return batches


def _dedupe_texts(values: list[str]) -> list[str]:
    return list(dict.fromkeys([value.strip() for value in values if value and value.strip()]))


def _coverage_warning_summary(
    *,
    sections: list[OutlineSection],
    requirements: list[RfpRequirementItem],
    units: list[DraftGenerationUnit],
    coverage: list[DraftRequirementCoverage],
    base_warnings: list[str],
    base_confirmation_required: bool,
) -> tuple[list[str], bool]:
    warnings = list(base_warnings)
    confirmation_required = base_confirmation_required
    if not requirements:
        return _dedupe_texts(warnings), confirmation_required

    unit_by_key = {unit.unit_key: unit for unit in units}
    primary_units = [
        unit_by_key[item.primary_unit_key]
        for item in coverage
        if item.primary_unit_key in unit_by_key
    ]
    section_modes = [normalize_writing_mode("", heading_text=build_heading_text(section)) for section in sections]

    if not any(unit.writing_mode in DELIVERY_WRITING_MODES for unit in units):
        warnings.append("현재 계획에는 실행형 또는 운영형 생성 단위가 없어 요구사항 대응 본문이 일반론으로 흐를 수 있습니다.")
        confirmation_required = True

    if sections and all(mode in BACKGROUND_LIKE_MODES for mode in section_modes):
        warnings.append("현재 목차는 배경·필요성·회사소개 성격에 치우쳐 있어 요구사항 중심 수행안을 충분히 담기 어렵습니다.")
        confirmation_required = True

    non_delivery_primary = [
        item.requirement_id
        for item in coverage
        if item.primary_unit_key in unit_by_key
        and unit_by_key[item.primary_unit_key].writing_mode not in DELIVERY_WRITING_MODES
    ]
    if non_delivery_primary:
        warnings.append(
            f"{len(non_delivery_primary)}개 요구사항의 주요 생성 단위가 배경/필요성/근거 성격에 배정되었습니다. 사업 수행 내용 계열 목차 보강이 필요할 수 있습니다."
        )
        if len(non_delivery_primary) >= max(3, len(requirements) // 2):
            confirmation_required = True

    if len(sections) == 1 and section_modes and section_modes[0] in BACKGROUND_LIKE_MODES:
        warnings.append("현재 목차가 사실상 단일 배경형 섹션이어서 요구사항을 충분히 구조화하기 어렵습니다.")
        confirmation_required = True

    primary_outline_ids = {item.primary_outline_section_id for item in coverage}
    if requirements and len(primary_outline_ids) == 1 and len(sections) > 1:
        only_section = next((section for section in sections if section.id in primary_outline_ids), None)
        if only_section is not None:
            warnings.append(
                f"모든 요구사항이 `{build_heading_text(only_section)}` 한 곳에 집중되어 있어 다른 목차와의 역할 분담이 약합니다."
            )

    return _dedupe_texts(warnings), confirmation_required


def _call_planner_overview(
    *,
    llm_service: LLMService,
    project_id: int,
    project_name: str,
    author_intent: str,
    extraction: RfpExtraction,
    sections: list[OutlineSection],
    requirements: list[RfpRequirementItem],
) -> StructuredDraftPlannerOverviewResult:
    try:
        heading_texts = [build_heading_text(section) for section in sections]
        referenced_playbook_keys = select_research_playbook_keys_for_headings(heading_texts)
        return llm_service.parse_chat_completion(
            model=llm_service.settings.openai_model_draft,
            system_prompt=DRAFT_PLANNER_OVERVIEW_SYSTEM_PROMPT,
            user_prompt=build_draft_planner_overview_prompt(
                project_name=project_name,
                author_intent=author_intent,
                rfp_summary=_rfp_summary_text(extraction),
                outline_summary=_outline_summary(sections),
                requirements_catalog=_requirements_catalog_for_overview(requirements),
                research_playbook_reference=build_selected_research_playbook_reference_text_for_headings(
                    heading_texts
                ),
            ),
            response_format=StructuredDraftPlannerOverviewResult,
            max_completion_tokens=5200,
            trace_project_id=project_id,
            trace_kind="draft.planner.overview",
            trace_metadata={
                "section_count": len(sections),
                "requirement_count": len(requirements),
                "author_intent_length": len(author_intent.strip()),
                "referenced_playbook_keys": referenced_playbook_keys,
            },
        )
    except (LLMConfigurationError, LLMResponseError) as exc:
        raise DraftGenerationError(f"AI planner overview failed: {exc}") from exc


def _call_planner_batch(
    *,
    llm_service: LLMService,
    project_id: int,
    project_name: str,
    author_intent: str,
    extraction: RfpExtraction,
    section_strategy_summary: str,
    requirements_batch: list[RfpRequirementItem],
    evaluation_items: list[EvaluationItem],
    assets: list[LibraryAsset],
    asset_text_index: dict[int, list[str]] | None,
    batch_index: int,
    batch_count: int,
    research_playbook_reference: str,
    referenced_playbook_keys: list[str],
    compact_requirement_details: bool = False,
    split_depth: int = 0,
) -> StructuredDraftPlannerBatchResult:
    if split_depth > MAX_PLANNER_BATCH_SPLIT_DEPTH:
        raise DraftGenerationError(
            "AI planner batch failed: requirement batch split depth exceeded the safe limit."
        )
    requirements_packet = _requirements_packet(requirements_batch)
    if compact_requirement_details:
        lines = []
        for requirement in requirements_batch:
            detail = (requirement.details or "").strip()
            lines.append(
                "\n".join(
                    [
                        f"[requirement_id={requirement.id}]",
                        f"번호: {requirement.requirement_no or '-'}",
                        f"제목: {(requirement.name or requirement.requirement_no or '요구사항').strip()}",
                        f"정의: {(requirement.definition or '-').strip()}",
                        f"세부 내용 요약: {detail[:1600] if detail else '-'}",
                    ]
                )
            )
        requirements_packet = "\n\n".join(lines)

    try:
        return llm_service.parse_chat_completion(
            model=llm_service.settings.openai_model_draft,
            system_prompt=DRAFT_PLANNER_BATCH_SYSTEM_PROMPT,
            user_prompt=build_draft_planner_batch_prompt(
                project_name=project_name,
                author_intent=author_intent,
                rfp_summary=_rfp_summary_text(extraction),
                section_strategy_summary=section_strategy_summary,
                requirements_packet=requirements_packet,
                evaluation_summary=_evaluation_summary(evaluation_items),
                asset_summary=_asset_summary(assets, asset_text_index=asset_text_index),
                batch_index=batch_index,
                batch_count=batch_count,
                research_playbook_reference=research_playbook_reference,
            ),
            response_format=StructuredDraftPlannerBatchResult,
            max_completion_tokens=6200,
            trace_project_id=project_id,
            trace_kind="draft.planner.batch",
            trace_metadata={
                "batch_index": batch_index,
                "batch_count": batch_count,
                "batch_requirement_ids": [item.id for item in requirements_batch],
                "compact_requirement_details": compact_requirement_details,
                "referenced_playbook_keys": referenced_playbook_keys,
            },
        )
    except (LLMConfigurationError, LLMResponseError) as exc:
        message = str(exc)
        if (
            ("LengthFinishReasonError" in message or "length limit" in message.lower())
            and len(requirements_batch) > 1
        ):
            midpoint = max(1, len(requirements_batch) // 2)
            left = _call_planner_batch(
                llm_service=llm_service,
                project_id=project_id,
                project_name=project_name,
                author_intent=author_intent,
                extraction=extraction,
                section_strategy_summary=section_strategy_summary,
                requirements_batch=requirements_batch[:midpoint],
                evaluation_items=evaluation_items,
                assets=assets,
                asset_text_index=asset_text_index,
                batch_index=batch_index,
                batch_count=batch_count,
                research_playbook_reference=research_playbook_reference,
                referenced_playbook_keys=referenced_playbook_keys,
                compact_requirement_details=compact_requirement_details,
                split_depth=split_depth + 1,
            )
            right = _call_planner_batch(
                llm_service=llm_service,
                project_id=project_id,
                project_name=project_name,
                author_intent=author_intent,
                extraction=extraction,
                section_strategy_summary=section_strategy_summary,
                requirements_batch=requirements_batch[midpoint:],
                evaluation_items=evaluation_items,
                assets=assets,
                asset_text_index=asset_text_index,
                batch_index=batch_index,
                batch_count=batch_count,
                research_playbook_reference=research_playbook_reference,
                referenced_playbook_keys=referenced_playbook_keys,
                compact_requirement_details=compact_requirement_details,
                split_depth=split_depth + 1,
            )
            return StructuredDraftPlannerBatchResult(
                generation_units=[*left.generation_units, *right.generation_units],
                requirement_coverage=[*left.requirement_coverage, *right.requirement_coverage],
            )
        if (
            ("LengthFinishReasonError" in message or "length limit" in message.lower())
            and not compact_requirement_details
        ):
            return _call_planner_batch(
                llm_service=llm_service,
                project_id=project_id,
                project_name=project_name,
                author_intent=author_intent,
                extraction=extraction,
                section_strategy_summary=section_strategy_summary,
                requirements_batch=requirements_batch,
                evaluation_items=evaluation_items,
                assets=assets,
                asset_text_index=asset_text_index,
                batch_index=batch_index,
                batch_count=batch_count,
                research_playbook_reference=research_playbook_reference,
                referenced_playbook_keys=referenced_playbook_keys,
                compact_requirement_details=True,
                split_depth=split_depth,
            )
        raise DraftGenerationError(f"AI planner batch failed: {exc}") from exc


def build_ai_draft_plan(
    *,
    llm_service: LLMService,
    project_id: int,
    project_name: str,
    author_intent: str,
    sections: list[OutlineSection],
    extraction: RfpExtraction,
    requirements: list[RfpRequirementItem],
    evaluation_items: list[EvaluationItem],
    assets: list[LibraryAsset],
    asset_text_index: dict[int, list[str]] | None = None,
) -> DraftPlanResult:
    warnings: list[str] = []
    if not sections:
        warnings.append("저장된 목차가 없습니다. Outline 페이지에서 목차를 먼저 저장해 주세요.")
    if not extraction.raw_text.strip():
        warnings.append("RFP 추출 결과가 없습니다. RFP 화면에서 추출을 먼저 실행해 주세요.")
    if warnings:
        return DraftPlanResult(
            ready=False,
            warnings=warnings,
            sections=[],
            author_intent=author_intent,
        )

    fingerprint = _planner_cache_fingerprint(
        project_name=project_name,
        author_intent=author_intent,
        sections=sections,
        extraction=extraction,
        requirements=requirements,
        evaluation_items=evaluation_items,
        assets=assets,
        asset_text_index=asset_text_index,
    )
    cached = _restore_cached_planner_result(
        project_id=project_id,
        fingerprint=fingerprint,
        sections=sections,
        requirements=requirements,
        evaluation_items=evaluation_items,
        assets=assets,
    )
    if cached is not None:
        return cached

    overview_result = _call_planner_overview(
        llm_service=llm_service,
        project_id=project_id,
        project_name=project_name,
        author_intent=author_intent,
        extraction=extraction,
        sections=sections,
        requirements=requirements,
    )
    section_by_id = {section.id: section for section in sections}
    heading_paths = _heading_paths(sections)
    requirement_by_id = {item.id: item for item in requirements}
    evaluation_by_id = {item.id: item for item in evaluation_items}
    asset_by_id = {item.id: item for item in assets}
    execution_section = _best_execution_section(sections)

    section_goal_by_id, guidance_by_id, section_mode_by_id, section_warning_by_id = _build_section_plan_lookup(
        overview_result.sections,
        sections,
    )
    section_strategy_summary = _section_strategy_summary(
        sections,
        section_goal_by_id=section_goal_by_id,
        guidance_by_id=guidance_by_id,
        mode_by_id=section_mode_by_id,
        warning_by_id=section_warning_by_id,
    )
    heading_texts = [build_heading_text(section) for section in sections]
    planner_research_playbook_reference = build_selected_research_playbook_reference_text_for_headings(
        heading_texts
    )
    planner_referenced_playbook_keys = select_research_playbook_keys_for_headings(heading_texts)

    requirement_batches = _build_requirement_batches(requirements)
    if len(requirement_batches) > MAX_PLANNER_BATCH_COUNT:
        raise DraftGenerationError(
            f"AI planner failed: requirement batch count exceeded the safe limit ({MAX_PLANNER_BATCH_COUNT})."
        )
    batch_results: list[StructuredDraftPlannerBatchResult] = []
    for batch_index, requirement_batch in enumerate(requirement_batches, start=1):
        batch_results.append(
            _call_planner_batch(
                llm_service=llm_service,
                project_id=project_id,
                project_name=project_name,
                author_intent=author_intent,
                extraction=extraction,
                section_strategy_summary=section_strategy_summary,
                requirements_batch=requirement_batch,
                evaluation_items=evaluation_items,
                assets=assets,
                asset_text_index=asset_text_index,
                batch_index=batch_index,
                batch_count=len(requirement_batches),
                research_playbook_reference=planner_research_playbook_reference,
                referenced_playbook_keys=planner_referenced_playbook_keys,
            )
        )

    units: list[DraftGenerationUnit] = []
    unit_by_key: dict[str, DraftGenerationUnit] = {}
    used_unit_keys: set[str] = set()
    planner_to_actual_unit_key: dict[str, str] = {}

    for batch_result in batch_results:
        for index, item in enumerate(batch_result.generation_units, start=1):
            section = section_by_id.get(item.outline_section_id, execution_section)
            raw_unit_key = item.unit_key.strip()
            unit_key = _clean_unit_key(
                raw_unit_key,
                outline_section_id=section.id,
                unit_index=len(units) + index,
            )
            suffix = 2
            base_key = unit_key
            collision_attempts = 0
            while unit_key in used_unit_keys:
                collision_attempts += 1
                if collision_attempts > MAX_UNIT_KEY_COLLISION_ATTEMPTS:
                    raise DraftGenerationError(
                        "AI planner failed: unit key collision attempts exceeded the safe limit."
                    )
                unit_key = f"{base_key}-{suffix}"
                suffix += 1
            used_unit_keys.add(unit_key)

            primary_ids = _unique_ids(
                [requirement_id for requirement_id in item.primary_requirement_ids if requirement_id in requirement_by_id]
            )
            secondary_ids = _unique_ids(
                [
                    requirement_id
                    for requirement_id in item.secondary_requirement_ids
                    if requirement_id in requirement_by_id and requirement_id not in primary_ids
                ]
            )
            evaluation_ids = _unique_ids(
                [evaluation_id for evaluation_id in item.evaluation_item_ids if evaluation_id in evaluation_by_id]
            )
            asset_ids = _unique_ids([asset_id for asset_id in item.asset_ids if asset_id in asset_by_id])
            writing_mode = normalize_writing_mode(
                item.writing_mode,
                heading_text=item.unit_title or build_heading_text(section),
            )
            unit_requirements = [
                requirement_by_id[requirement_id]
                for requirement_id in primary_ids + secondary_ids
                if requirement_id in requirement_by_id
            ]
            unit_pattern = infer_unit_pattern(
                writing_mode=writing_mode,
                heading_text=item.unit_title.strip() or build_heading_text(section),
                requirements=unit_requirements,
                requested_pattern=item.unit_pattern,
            )
            search_tasks = _normalize_search_tasks(item.search_tasks)

            unit = DraftGenerationUnit(
                unit_key=unit_key,
                outline_section_id=section.id,
                unit_title=item.unit_title.strip() or f"{build_heading_text(section)} 생성 단위",
                section_heading_text=build_heading_text(section),
                section_goal=section_goal_by_id[section.id],
                unit_goal=item.unit_goal.strip() or section_goal_by_id[section.id],
                writing_instruction=item.writing_instruction.strip() or guidance_by_id[section.id],
                writing_mode=writing_mode,
                unit_pattern=unit_pattern,
                required_aspects=_normalize_required_aspects(
                    raw_aspects=item.required_aspects,
                    writing_mode=writing_mode,
                    unit_pattern=unit_pattern,
                    requirements=unit_requirements,
                    heading_text=item.unit_title.strip() or build_heading_text(section),
                ),
                primary_requirement_ids=primary_ids,
                secondary_requirement_ids=secondary_ids,
                evaluation_item_ids=evaluation_ids,
                asset_ids=asset_ids,
                company_facts=_company_facts_from_assets(
                    heading_text=item.unit_title.strip() or build_heading_text(section),
                    assets=[asset_by_id[asset_id] for asset_id in asset_ids],
                    asset_text_index=asset_text_index,
                ),
                search_tasks=search_tasks,
                outline_fit_warning=(item.outline_fit_warning or section_warning_by_id.get(section.id, "")).strip(),
            )
            units.append(unit)
            if len(units) > MAX_GENERATION_UNITS:
                raise DraftGenerationError(
                    f"AI planner failed: generation unit count exceeded the safe limit ({MAX_GENERATION_UNITS})."
                )
            unit_by_key[unit.unit_key] = unit
            if raw_unit_key:
                planner_to_actual_unit_key[raw_unit_key] = unit.unit_key

    for section in sections:
        if any(unit.outline_section_id == section.id for unit in units):
            continue
        default_key = _clean_unit_key(
            f"section-{section.id}-default",
            outline_section_id=section.id,
            unit_index=len(units) + 1,
        )
        if default_key in used_unit_keys:
            default_key = f"{default_key}-{len(units) + 1}"
        used_unit_keys.add(default_key)
        default_mode = section_mode_by_id.get(section.id, "execution")
        default_unit = DraftGenerationUnit(
            unit_key=default_key,
            outline_section_id=section.id,
            unit_title=build_heading_text(section),
            section_heading_text=build_heading_text(section),
            section_goal=section_goal_by_id[section.id],
            unit_goal=section_goal_by_id[section.id],
            writing_instruction=guidance_by_id[section.id],
            writing_mode=default_mode,
            unit_pattern=infer_unit_pattern(
                writing_mode=default_mode,
                heading_text=build_heading_text(section),
                requirements=[],
            ),
            required_aspects=default_required_aspects_for_pattern(
                infer_unit_pattern(
                    writing_mode=default_mode,
                    heading_text=build_heading_text(section),
                    requirements=[],
                )
            ),
            search_tasks=[],
            outline_fit_warning=section_warning_by_id.get(section.id, ""),
        )
        units.append(default_unit)
        if len(units) > MAX_GENERATION_UNITS:
            raise DraftGenerationError(
                f"AI planner failed: generation unit count exceeded the safe limit ({MAX_GENERATION_UNITS})."
            )
        unit_by_key[default_key] = default_unit

    requirement_primary_by_id: dict[int, str] = {}
    requirement_secondary_by_id: dict[int, list[str]] = defaultdict(list)
    requirement_rationale_by_id: dict[int, str] = {}

    for batch_result in batch_results:
        for item in batch_result.requirement_coverage:
            if item.requirement_id not in requirement_by_id:
                continue
            actual_primary_key = planner_to_actual_unit_key.get(
                item.primary_unit_key,
                item.primary_unit_key,
            )
            if actual_primary_key in unit_by_key:
                requirement_primary_by_id[item.requirement_id] = actual_primary_key
            valid_secondaries = [
                planner_to_actual_unit_key.get(unit_key, unit_key)
                for unit_key in item.secondary_unit_keys
                if planner_to_actual_unit_key.get(unit_key, unit_key) in unit_by_key
                and planner_to_actual_unit_key.get(unit_key, unit_key)
                != requirement_primary_by_id.get(item.requirement_id)
            ]
            if valid_secondaries:
                requirement_secondary_by_id[item.requirement_id] = list(dict.fromkeys(valid_secondaries))
            if item.rationale.strip():
                requirement_rationale_by_id[item.requirement_id] = item.rationale.strip()

    for unit in units:
        for requirement_id in unit.primary_requirement_ids:
            requirement_primary_by_id.setdefault(requirement_id, unit.unit_key)
        for requirement_id in unit.secondary_requirement_ids:
            secondary_keys = requirement_secondary_by_id.setdefault(requirement_id, [])
            if unit.unit_key not in secondary_keys:
                secondary_keys.append(unit.unit_key)

    uncovered_requirements = [
        requirement
        for requirement in sorted(requirements, key=lambda item: (item.sort_order, item.id))
        if requirement.id not in requirement_primary_by_id
    ]
    fallback_bundles = _build_requirement_batches(uncovered_requirements, max_items=3, max_chars=4200)
    if len(fallback_bundles) > MAX_FALLBACK_BUNDLES:
        raise DraftGenerationError(
            f"AI planner failed: fallback bundle count exceeded the safe limit ({MAX_FALLBACK_BUNDLES})."
        )
    for bundle_index, bundle in enumerate(fallback_bundles, start=1):
        if not bundle:
            continue
        unit_key = f"fallback-{execution_section.id}-{bundle_index}"
        collision_attempts = 0
        while unit_key in used_unit_keys:
            collision_attempts += 1
            if collision_attempts > MAX_UNIT_KEY_COLLISION_ATTEMPTS:
                raise DraftGenerationError(
                    "AI planner failed: fallback unit key collision attempts exceeded the safe limit."
                )
            unit_key = f"{unit_key}-x"
        used_unit_keys.add(unit_key)
        fallback_unit = DraftGenerationUnit(
            unit_key=unit_key,
            outline_section_id=execution_section.id,
            unit_title=_fallback_unit_title(bundle, bundle_index),
            section_heading_text=build_heading_text(execution_section),
            section_goal=section_goal_by_id[execution_section.id],
            unit_goal="누락된 요구사항을 실행 계획 중심으로 구체화한다.",
            writing_instruction=guidance_by_id[execution_section.id],
            writing_mode="execution",
            unit_pattern=infer_unit_pattern(
                writing_mode="execution",
                heading_text=build_heading_text(execution_section),
                requirements=bundle,
            ),
            required_aspects=default_required_aspects_for_pattern(
                infer_unit_pattern(
                    writing_mode="execution",
                    heading_text=build_heading_text(execution_section),
                    requirements=bundle,
                )
            ),
            primary_requirement_ids=[item.id for item in bundle],
            search_tasks=[],
            outline_fit_warning="AI planner 결과에서 누락된 요구사항을 보정한 fallback 생성 단위입니다.",
        )
        units.append(fallback_unit)
        if len(units) > MAX_GENERATION_UNITS:
            raise DraftGenerationError(
                f"AI planner failed: generation unit count exceeded the safe limit ({MAX_GENERATION_UNITS})."
            )
        unit_by_key[fallback_unit.unit_key] = fallback_unit
        for requirement in bundle:
            requirement_primary_by_id[requirement.id] = fallback_unit.unit_key
            requirement_rationale_by_id.setdefault(
                requirement.id,
                "AI planner 결과에서 누락되어 실행형 fallback 생성 단위로 보정했습니다.",
            )

    coverage: list[DraftRequirementCoverage] = []
    for requirement in sorted(requirements, key=lambda item: (item.sort_order, item.id)):
        primary_unit_key = requirement_primary_by_id.get(requirement.id)
        if primary_unit_key is None:
            continue
        primary_unit = unit_by_key[primary_unit_key]
        secondary_unit_keys = [
            unit_key
            for unit_key in requirement_secondary_by_id.get(requirement.id, [])
            if unit_key in unit_by_key and unit_key != primary_unit_key
        ]
        coverage.append(
            DraftRequirementCoverage(
                requirement_id=requirement.id,
                primary_unit_key=primary_unit_key,
                primary_outline_section_id=primary_unit.outline_section_id,
                secondary_unit_keys=list(dict.fromkeys(secondary_unit_keys)),
                rationale=requirement_rationale_by_id.get(requirement.id, ""),
            )
        )

    coverage_warnings, confirmation_required = _coverage_warning_summary(
        sections=sections,
        requirements=requirements,
        units=units,
        coverage=coverage,
        base_warnings=overview_result.coverage_warnings,
        base_confirmation_required=overview_result.generation_requires_confirmation,
    )

    units_by_section: dict[int, list[DraftGenerationUnit]] = defaultdict(list)
    for unit in units:
        units_by_section[unit.outline_section_id].append(unit)

    section_plans: list[DraftSectionPlan] = []
    for section in sections:
        related_units = units_by_section.get(section.id, [])
        requirement_ids: list[int] = []
        evaluation_ids: list[int] = []
        asset_ids: list[int] = []
        company_facts: list[str] = []
        search_tasks: list[PlannedSearchTask] = []
        for unit in related_units:
            requirement_ids.extend(unit.primary_requirement_ids)
            requirement_ids.extend(unit.secondary_requirement_ids)
            evaluation_ids.extend(unit.evaluation_item_ids)
            asset_ids.extend(unit.asset_ids)
            company_facts.extend(unit.company_facts)
            search_tasks.extend(unit.search_tasks)

        deduped_company_facts = _dedupe_texts(company_facts)[:16]
        section_plans.append(
            DraftSectionPlan(
                section=section,
                heading_text=build_heading_text(section),
                heading_path=heading_paths.get(section.id, [build_heading_text(section)]),
                section_goal=section_goal_by_id[section.id],
                assigned_requirements=[
                    requirement_by_id[item_id]
                    for item_id in _unique_ids(requirement_ids)
                    if item_id in requirement_by_id
                ],
                assigned_evaluation_items=[
                    evaluation_by_id[item_id]
                    for item_id in _unique_ids(evaluation_ids)
                    if item_id in evaluation_by_id
                ],
                assigned_assets=[
                    asset_by_id[item_id]
                    for item_id in _unique_ids(asset_ids)
                    if item_id in asset_by_id
                ],
                assigned_company_facts=deduped_company_facts,
                draft_guidance=guidance_by_id[section.id],
                search_tasks=_dedupe_search_tasks(search_tasks),
            )
        )

    plan_result = DraftPlanResult(
        ready=True,
        warnings=warnings,
        sections=section_plans,
        author_intent=author_intent,
        planner_summary=_normalize_planner_summary(overview_result.planner_summary),
        planner_mode="ai_v2",
        generation_units=units,
        requirement_coverage=coverage,
        coverage_warnings=coverage_warnings,
        generation_requires_confirmation=confirmation_required,
    )
    _save_cached_planner_result(
        project_id=project_id,
        fingerprint=fingerprint,
        plan_result=plan_result,
    )
    return plan_result
