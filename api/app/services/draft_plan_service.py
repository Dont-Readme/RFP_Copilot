from __future__ import annotations

from dataclasses import dataclass, field
import re

from app.models.evaluation import EvaluationItem
from app.models.library import LibraryAsset
from app.models.outline import OutlineSection
from app.models.rfp import RfpExtraction, RfpRequirementItem


@dataclass(frozen=True)
class PlannedSearchTask:
    topic: str
    reason: str
    freshness_required: bool = True
    expected_output: str = ""
    purpose: str = ""
    allowed_domains: list[str] = field(default_factory=list)
    max_results: int = 4


@dataclass(frozen=True)
class DraftSectionPlan:
    section: OutlineSection
    heading_text: str
    heading_path: list[str]
    section_goal: str
    assigned_requirements: list[RfpRequirementItem] = field(default_factory=list)
    assigned_evaluation_items: list[EvaluationItem] = field(default_factory=list)
    assigned_assets: list[LibraryAsset] = field(default_factory=list)
    assigned_company_facts: list[str] = field(default_factory=list)
    draft_guidance: str = ""
    search_tasks: list[PlannedSearchTask] = field(default_factory=list)
    status: str = "planned"


@dataclass(frozen=True)
class DraftGenerationUnit:
    unit_key: str
    outline_section_id: int
    unit_title: str
    section_heading_text: str
    section_goal: str
    unit_goal: str
    writing_instruction: str
    writing_mode: str = "execution"
    unit_pattern: str = "functional_workflow"
    required_aspects: list[str] = field(default_factory=list)
    primary_requirement_ids: list[int] = field(default_factory=list)
    secondary_requirement_ids: list[int] = field(default_factory=list)
    evaluation_item_ids: list[int] = field(default_factory=list)
    asset_ids: list[int] = field(default_factory=list)
    company_facts: list[str] = field(default_factory=list)
    search_tasks: list[PlannedSearchTask] = field(default_factory=list)
    outline_fit_warning: str = ""


@dataclass(frozen=True)
class DraftRequirementCoverage:
    requirement_id: int
    primary_unit_key: str
    primary_outline_section_id: int
    secondary_unit_keys: list[str] = field(default_factory=list)
    rationale: str = ""


@dataclass(frozen=True)
class DraftPlanResult:
    ready: bool
    warnings: list[str]
    sections: list[DraftSectionPlan]
    author_intent: str = ""
    planner_summary: str = ""
    planner_mode: str = "rule_based"
    generation_units: list[DraftGenerationUnit] = field(default_factory=list)
    requirement_coverage: list[DraftRequirementCoverage] = field(default_factory=list)
    coverage_warnings: list[str] = field(default_factory=list)
    generation_requires_confirmation: bool = False


@dataclass(frozen=True)
class PlannerRequirementDiagnostic:
    requirement_id: int
    requirement_no: str
    name: str
    definition: str
    details: str
    score: int
    matched_tokens: list[str]
    selected: bool


@dataclass(frozen=True)
class PlannerEvaluationDiagnostic:
    evaluation_item_id: int
    item: str
    score_text: str
    notes: str
    score: int
    matched_tokens: list[str]
    selected: bool


@dataclass(frozen=True)
class PlannerAssetDiagnostic:
    asset_id: int
    category: str
    title: str
    score: int
    matched_tokens: list[str]
    compact_heading_match: bool
    selected: bool
    snippet_previews: list[str]


@dataclass(frozen=True)
class DraftSectionPlanDebug:
    section_id: int
    heading_text: str
    heading_path: list[str]
    section_tokens: list[str]
    section_goal: str
    draft_guidance: str
    assigned_company_facts: list[str]
    search_tasks: list[PlannedSearchTask]
    requirement_candidates: list[PlannerRequirementDiagnostic]
    evaluation_candidates: list[PlannerEvaluationDiagnostic]
    asset_candidates: list[PlannerAssetDiagnostic]


@dataclass(frozen=True)
class DraftPlanDebugResult:
    ready: bool
    warnings: list[str]
    sections: list[DraftSectionPlanDebug]


SECTION_PLAYBOOKS = (
    (
        ("시장", "동향", "경쟁", "환경"),
        "사업 추진 배경과 외부 환경을 설명하고, 수요 또는 경쟁 맥락을 제안 대응 논리로 연결한다.",
        "배경 -> 현재 환경/수요 -> 우리 대응 방향 -> 기대 효과 흐름으로 작성한다.",
    ),
    (
        ("사업화", "확산", "판로", "수익"),
        "사업화 방향과 적용 확산 전략을 실행 관점에서 제시한다.",
        "목표 -> 실행 수단 -> 협업/운영 방식 -> 기대 효과 흐름으로 작성한다.",
    ),
    (
        ("수행체계", "추진체계", "조직", "인력", "역할"),
        "수행 조직과 역할 분담, 품질/보고 체계를 제안서 문체로 정리한다.",
        "역할 구성 -> 운영 방식 -> 관리 체계 -> 보고/품질 확보 순으로 작성한다.",
    ),
    (
        ("일정", "로드맵", "계획", "마일스톤"),
        "단계별 수행 일정과 산출물 흐름을 정리한다.",
        "단계 구분 -> 핵심 작업 -> 산출물/검증 포인트 흐름으로 작성한다.",
    ),
    (
        ("실적", "레퍼런스", "사례"),
        "유사 사례와 수행 역량을 신뢰 확보 관점에서 정리한다.",
        "관련성 -> 수행 경험 -> 재사용 가능한 강점 -> 본 사업 적용 관점으로 작성한다.",
    ),
)

SEARCH_RULES = (
    (
        ("특허", "지식재산", "지재권"),
        "최신 특허 및 지식재산 동향",
        "최신 특허/출원 또는 관련 기술 흐름 확인이 필요합니다.",
        "최신 특허, 출원, 공개 기술 흐름 요약",
    ),
    (
        ("시장", "동향", "경쟁", "환경"),
        "최신 시장 및 경쟁 동향",
        "최신 시장·경쟁 환경 확인이 필요합니다.",
        "최신 시장 변화, 경쟁 구도, 주요 트렌드 요약",
    ),
    (
        ("규제", "법령", "인증", "표준", "가이드라인"),
        "최신 규제 및 인증 동향",
        "최신 규제·인증·표준 확인이 필요합니다.",
        "관련 법령, 인증, 가이드라인 변화 요약",
    ),
)

ASSET_CATEGORY_HINTS: dict[str, str] = {
    "회사소개": "회사 소개 기업 개요 일반현황 연혁 비전 조직 핵심역량",
    "제품": "제품 서비스 솔루션 플랫폼 기술 기술력 스마트팜",
    "실적": "실적 수행사례 레퍼런스 사업경험 구축사례",
    "인력": "인력 조직 수행체계 참여인력 인원 전문인력",
    "특허": "특허 지식재산 지재권 저작권 인증 기술력",
    "재무": "재무 매출 손익 안정성 신용",
    "레퍼런스": "레퍼런스 사례 실적 고객 구축",
    "기타": "",
}
INTERNAL_EVIDENCE_SEARCH_KEYWORDS = (
    "회사",
    "소개",
    "특허",
    "지식재산",
    "지재권",
    "저작권",
    "인증",
    "기술력",
    "실적",
    "레퍼런스",
    "인력",
    "조직",
    "제품",
    "서비스",
    "솔루션",
)


def build_heading_text(section: OutlineSection) -> str:
    label = (section.display_label or "").strip()
    title = section.title.strip()
    if label:
        return f"{label} {title}".strip()
    return title


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[A-Za-z0-9가-힣]+", text.lower()) if len(token) >= 2}


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def _heading_text(section: OutlineSection) -> str:
    return build_heading_text(section)


def _build_heading_paths(sections: list[OutlineSection]) -> dict[int, list[str]]:
    paths: dict[int, list[str]] = {}
    stack: list[str] = []

    for section in sections:
        depth = max(1, section.depth)
        stack = stack[: depth - 1]
        stack.append(_heading_text(section))
        paths[section.id] = stack.copy()

    return paths


def _score_text(section_tokens: set[str], *candidate_texts: str) -> int:
    candidate_tokens = _tokens(" ".join(text for text in candidate_texts if text))
    if not section_tokens or not candidate_tokens:
        return 0
    overlap = section_tokens & candidate_tokens
    return len(overlap)


def _matched_tokens(section_tokens: set[str], *candidate_texts: str) -> list[str]:
    candidate_tokens = _tokens(" ".join(text for text in candidate_texts if text))
    if not section_tokens or not candidate_tokens:
        return []
    return sorted(section_tokens & candidate_tokens)


def _rank_requirements(
    *,
    heading_text: str,
    requirements: list[RfpRequirementItem],
    limit: int = 4,
) -> list[RfpRequirementItem]:
    section_tokens = _tokens(heading_text)
    ranked = sorted(
        requirements,
        key=lambda requirement: (
            -_score_text(
                section_tokens,
                requirement.requirement_no,
                requirement.name,
                requirement.definition,
                requirement.details,
            ),
            requirement.sort_order,
            requirement.id,
        ),
    )
    matched = [
        requirement
        for requirement in ranked
        if _score_text(
            section_tokens,
            requirement.requirement_no,
            requirement.name,
            requirement.definition,
            requirement.details,
        )
        > 0
    ]
    return matched[:limit]


def _requirement_diagnostics(
    *,
    heading_text: str,
    requirements: list[RfpRequirementItem],
    limit: int = 8,
) -> list[PlannerRequirementDiagnostic]:
    section_tokens = _tokens(heading_text)
    diagnostics = [
        PlannerRequirementDiagnostic(
            requirement_id=requirement.id,
            requirement_no=requirement.requirement_no,
            name=requirement.name,
            definition=requirement.definition,
            details=requirement.details,
            score=_score_text(
                section_tokens,
                requirement.requirement_no,
                requirement.name,
                requirement.definition,
                requirement.details,
            ),
            matched_tokens=_matched_tokens(
                section_tokens,
                requirement.requirement_no,
                requirement.name,
                requirement.definition,
                requirement.details,
            ),
            selected=False,
        )
        for requirement in requirements
    ]
    ranked = sorted(
        diagnostics,
        key=lambda item: (
            -item.score,
            next(
                (
                    requirement.sort_order
                    for requirement in requirements
                    if requirement.id == item.requirement_id
                ),
                0,
            ),
            item.requirement_id,
        ),
    )
    selected_ids = set([item.requirement_id for item in ranked if item.score > 0][:4])
    return [
        PlannerRequirementDiagnostic(
            requirement_id=item.requirement_id,
            requirement_no=item.requirement_no,
            name=item.name,
            definition=item.definition,
            details=item.details,
            score=item.score,
            matched_tokens=item.matched_tokens,
            selected=item.requirement_id in selected_ids,
        )
        for item in ranked[:limit]
    ]


def _rank_evaluation_items(
    *,
    heading_text: str,
    evaluation_items: list[EvaluationItem],
    limit: int = 3,
) -> list[EvaluationItem]:
    section_tokens = _tokens(heading_text)
    ranked = sorted(
        evaluation_items,
        key=lambda item: (-_score_text(section_tokens, item.item, item.score, item.notes), item.id),
    )
    matched = [
        item
        for item in ranked
        if _score_text(section_tokens, item.item, item.score, item.notes) > 0
    ]
    return matched[:limit]


def _evaluation_diagnostics(
    *,
    heading_text: str,
    evaluation_items: list[EvaluationItem],
    limit: int = 6,
) -> list[PlannerEvaluationDiagnostic]:
    section_tokens = _tokens(heading_text)
    diagnostics = [
        PlannerEvaluationDiagnostic(
            evaluation_item_id=item.id,
            item=item.item,
            score_text=item.score,
            notes=item.notes,
            score=_score_text(section_tokens, item.item, item.score, item.notes),
            matched_tokens=_matched_tokens(section_tokens, item.item, item.score, item.notes),
            selected=False,
        )
        for item in evaluation_items
    ]
    ranked = sorted(
        diagnostics,
        key=lambda item: (-item.score, item.evaluation_item_id),
    )
    selected_ids = set([item.evaluation_item_id for item in ranked if item.score > 0][:3])
    return [
        PlannerEvaluationDiagnostic(
            evaluation_item_id=item.evaluation_item_id,
            item=item.item,
            score_text=item.score_text,
            notes=item.notes,
            score=item.score,
            matched_tokens=item.matched_tokens,
            selected=item.evaluation_item_id in selected_ids,
        )
        for item in ranked[:limit]
    ]


def _rank_assets(
    *,
    heading_text: str,
    assets: list[LibraryAsset],
    asset_text_index: dict[int, list[str]] | None = None,
    limit: int = 3,
) -> list[LibraryAsset]:
    section_tokens = _tokens(heading_text)
    heading_compact = _compact(heading_text)

    def asset_score(asset: LibraryAsset) -> int:
        asset_hint_text = ASSET_CATEGORY_HINTS.get(asset.category, "")
        asset_texts = list((asset_text_index or {}).get(asset.id, []))[:2]
        score = _score_text(section_tokens, asset.category, asset.title, asset_hint_text, *asset_texts)
        compact_haystack = _compact(" ".join([asset.category, asset.title, asset_hint_text, *asset_texts]))
        if heading_compact and heading_compact and heading_compact in compact_haystack:
            score += 4
        return score

    ranked = sorted(
        assets,
        key=lambda asset: (-asset_score(asset), asset.id),
    )
    matched = [asset for asset in ranked if asset_score(asset) > 0]
    return matched[:limit]


def _asset_diagnostics(
    *,
    heading_text: str,
    assets: list[LibraryAsset],
    asset_text_index: dict[int, list[str]] | None = None,
    limit: int = 6,
) -> list[PlannerAssetDiagnostic]:
    section_tokens = _tokens(heading_text)
    heading_compact = _compact(heading_text)

    diagnostics: list[PlannerAssetDiagnostic] = []
    for asset in assets:
        asset_hint_text = ASSET_CATEGORY_HINTS.get(asset.category, "")
        asset_texts = list((asset_text_index or {}).get(asset.id, []))[:2]
        matched_tokens = _matched_tokens(
            section_tokens,
            asset.category,
            asset.title,
            asset_hint_text,
            *asset_texts,
        )
        compact_haystack = _compact(" ".join([asset.category, asset.title, asset_hint_text, *asset_texts]))
        compact_heading_match = bool(heading_compact and heading_compact in compact_haystack)
        score = len(matched_tokens) + (4 if compact_heading_match else 0)
        diagnostics.append(
            PlannerAssetDiagnostic(
                asset_id=asset.id,
                category=asset.category,
                title=asset.title,
                score=score,
                matched_tokens=matched_tokens,
                compact_heading_match=compact_heading_match,
                selected=False,
                snippet_previews=[re.sub(r"\s+", " ", text).strip()[:220] for text in asset_texts if text.strip()],
            )
        )

    ranked = sorted(diagnostics, key=lambda item: (-item.score, item.asset_id))
    selected_ids = set([item.asset_id for item in ranked if item.score > 0][:3])
    visible = ranked[:limit]
    return [
        PlannerAssetDiagnostic(
            asset_id=item.asset_id,
            category=item.category,
            title=item.title,
            score=item.score,
            matched_tokens=item.matched_tokens,
            compact_heading_match=item.compact_heading_match,
            selected=item.asset_id in selected_ids,
            snippet_previews=item.snippet_previews,
        )
        for item in visible
    ]


def _company_facts_from_assets(
    *,
    heading_text: str,
    assets: list[LibraryAsset],
    asset_text_index: dict[int, list[str]] | None = None,
) -> list[str]:
    if not assets:
        return []

    section_tokens = _tokens(heading_text)
    lines: list[str] = []
    for asset in assets:
        lines.append(f"[{asset.category}] {asset.title}".strip())
        snippets = list((asset_text_index or {}).get(asset.id, []))
        if not snippets:
            continue
        ranked_snippets = sorted(
            snippets,
            key=lambda text: (-_score_text(section_tokens, asset.category, asset.title, text), len(text)),
        )
        selected = [snippet for snippet in ranked_snippets if _score_text(section_tokens, asset.category, asset.title, snippet) > 0]
        if not selected:
            selected = ranked_snippets
        for snippet in selected[:2]:
            compact = re.sub(r"\s+", " ", snippet).strip()
            if compact:
                lines.append(f"- {compact[:420]}")
    return lines[:9]


def _playbook_for_heading(heading_text: str) -> tuple[str, str]:
    normalized_heading = heading_text.replace(" ", "")
    for keywords, goal, guidance in SECTION_PLAYBOOKS:
        if any(keyword in normalized_heading for keyword in keywords):
            return goal, guidance
    return (
        "해당 목차의 목적과 수행 방안을 공공 제안서 문체로 구체화한다.",
        "배경 -> 대응 방향 -> 실행 방안 -> 기대 효과 흐름으로 작성한다.",
    )


def _search_tasks_for_heading(
    *,
    section: OutlineSection,
    heading_text: str,
    project_name: str,
    assigned_assets: list[LibraryAsset],
) -> list[PlannedSearchTask]:
    normalized_heading = heading_text.replace(" ", "")
    tasks: list[PlannedSearchTask] = []

    if section.needs_search:
        tasks.append(
            PlannedSearchTask(
                topic=f"{project_name} {heading_text}",
                reason="사용자가 이 목차를 검색 필요 대상으로 표시했습니다.",
                freshness_required=True,
                expected_output="최신 관련 정보 요약",
            )
        )

    if assigned_assets and any(keyword in normalized_heading for keyword in INTERNAL_EVIDENCE_SEARCH_KEYWORDS):
        return tasks

    for keywords, suffix, reason, expected_output in SEARCH_RULES:
        if not any(keyword in normalized_heading for keyword in keywords):
            continue
        tasks.append(
            PlannedSearchTask(
                topic=f"{project_name} {suffix}",
                reason=reason,
                freshness_required=True,
                expected_output=expected_output,
            )
        )

    deduped: list[PlannedSearchTask] = []
    seen: set[str] = set()
    for task in tasks:
        if task.topic in seen:
            continue
        seen.add(task.topic)
        deduped.append(task)
    return deduped


def build_draft_plan(
    *,
    project_name: str,
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

    heading_paths = _build_heading_paths(sections)
    section_plans: list[DraftSectionPlan] = []

    for section in sections:
        heading_text = _heading_text(section)
        heading_path = heading_paths.get(section.id, [heading_text])
        section_requirements = _rank_requirements(heading_text=heading_text, requirements=requirements)
        section_evaluation_items = _rank_evaluation_items(
            heading_text=heading_text,
            evaluation_items=evaluation_items,
        )
        section_assets = _rank_assets(
            heading_text=heading_text,
            assets=assets,
            asset_text_index=asset_text_index,
        )
        section_goal, draft_guidance = _playbook_for_heading(heading_text)
        search_tasks = _search_tasks_for_heading(
            section=section,
            heading_text=heading_text,
            project_name=project_name,
            assigned_assets=section_assets,
        )

        section_plans.append(
            DraftSectionPlan(
                section=section,
                heading_text=heading_text,
                heading_path=heading_path,
                section_goal=section_goal,
                assigned_requirements=section_requirements,
                assigned_evaluation_items=section_evaluation_items,
                assigned_assets=section_assets,
                assigned_company_facts=_company_facts_from_assets(
                    heading_text=heading_text,
                    assets=section_assets,
                    asset_text_index=asset_text_index,
                ),
                draft_guidance=draft_guidance,
                search_tasks=search_tasks,
            )
        )

    return DraftPlanResult(
        ready=bool(sections) and bool(extraction.raw_text.strip()),
        warnings=warnings,
        sections=section_plans,
    )


def build_draft_plan_debug(
    *,
    project_name: str,
    sections: list[OutlineSection],
    extraction: RfpExtraction,
    requirements: list[RfpRequirementItem],
    evaluation_items: list[EvaluationItem],
    assets: list[LibraryAsset],
    asset_text_index: dict[int, list[str]] | None = None,
) -> DraftPlanDebugResult:
    warnings: list[str] = []
    if not sections:
        warnings.append("저장된 목차가 없습니다. Outline 페이지에서 목차를 먼저 저장해 주세요.")
    if not extraction.raw_text.strip():
        warnings.append("RFP 추출 결과가 없습니다. RFP 화면에서 추출을 먼저 실행해 주세요.")

    heading_paths = _build_heading_paths(sections)
    section_debugs: list[DraftSectionPlanDebug] = []

    for section in sections:
        heading_text = _heading_text(section)
        heading_path = heading_paths.get(section.id, [heading_text])
        selected_assets = _rank_assets(
            heading_text=heading_text,
            assets=assets,
            asset_text_index=asset_text_index,
        )
        section_goal, draft_guidance = _playbook_for_heading(heading_text)
        search_tasks = _search_tasks_for_heading(
            section=section,
            heading_text=heading_text,
            project_name=project_name,
            assigned_assets=selected_assets,
        )
        section_debugs.append(
            DraftSectionPlanDebug(
                section_id=section.id,
                heading_text=heading_text,
                heading_path=heading_path,
                section_tokens=sorted(_tokens(heading_text)),
                section_goal=section_goal,
                draft_guidance=draft_guidance,
                assigned_company_facts=_company_facts_from_assets(
                    heading_text=heading_text,
                    assets=selected_assets,
                    asset_text_index=asset_text_index,
                ),
                search_tasks=search_tasks,
                requirement_candidates=_requirement_diagnostics(
                    heading_text=heading_text,
                    requirements=requirements,
                ),
                evaluation_candidates=_evaluation_diagnostics(
                    heading_text=heading_text,
                    evaluation_items=evaluation_items,
                ),
                asset_candidates=_asset_diagnostics(
                    heading_text=heading_text,
                    assets=assets,
                    asset_text_index=asset_text_index,
                ),
            )
        )

    return DraftPlanDebugResult(
        ready=bool(sections) and bool(extraction.raw_text.strip()),
        warnings=warnings,
        sections=section_debugs,
    )
