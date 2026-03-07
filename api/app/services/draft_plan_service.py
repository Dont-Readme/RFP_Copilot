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
class DraftPlanResult:
    ready: bool
    warnings: list[str]
    sections: list[DraftSectionPlan]


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


def build_heading_text(section: OutlineSection) -> str:
    label = (section.display_label or "").strip()
    title = section.title.strip()
    if label:
        return f"{label} {title}".strip()
    return title


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[A-Za-z0-9가-힣]+", text.lower()) if len(token) >= 2}


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


def _rank_assets(
    *,
    heading_text: str,
    assets: list[LibraryAsset],
    limit: int = 3,
) -> list[LibraryAsset]:
    section_tokens = _tokens(heading_text)
    ranked = sorted(
        assets,
        key=lambda asset: (-_score_text(section_tokens, asset.category, asset.title), asset.id),
    )
    matched = [
        asset for asset in ranked if _score_text(section_tokens, asset.category, asset.title) > 0
    ]
    return matched[:limit]


def _company_facts_from_assets(assets: list[LibraryAsset]) -> list[str]:
    return [f"{asset.category}: {asset.title}".strip(": ") for asset in assets]


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
        section_assets = _rank_assets(heading_text=heading_text, assets=assets)
        section_goal, draft_guidance = _playbook_for_heading(heading_text)
        search_tasks = _search_tasks_for_heading(
            section=section,
            heading_text=heading_text,
            project_name=project_name,
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
                assigned_company_facts=_company_facts_from_assets(section_assets),
                draft_guidance=draft_guidance,
                search_tasks=search_tasks,
            )
        )

    return DraftPlanResult(
        ready=bool(sections) and bool(extraction.raw_text.strip()),
        warnings=warnings,
        sections=section_plans,
    )
