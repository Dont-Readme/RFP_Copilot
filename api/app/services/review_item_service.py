from __future__ import annotations

import re
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from app.models.outline import OutlineSection

SYSTEM_REVIEW_PREFIX = "[확인 필요(시스템)]"
_SYSTEM_REVIEW_PATTERN = re.compile(r"^\[확인 필요\(시스템\)\]\s*(.*)$")


class ReviewItemPayload(BaseModel):
    outline_section_id: int | None = None
    section_heading_text: str
    question_text: str
    category: str = "missing_evidence"
    severity: str = "medium"
    source_agent: str = "reviewer"


FALLBACK_REVIEW_RULES = (
    {
        "heading_keywords": ("시장조사", "시장분석", "경쟁분석", "시장", "경쟁", "동향"),
        "summary_keywords": ("시장", "산업", "경쟁사", "경쟁제품", "동향", "수요", "공급", "벤치마크", "현황"),
        "message": "시장 현황, 경쟁사, 수요 근거가 RFP 요약에 없어 내용 확인이 필요합니다.",
    },
    {
        "heading_keywords": ("사업화전략", "사업화", "확산전략", "판로전략", "수익모델", "비즈니스모델"),
        "summary_keywords": ("사업화", "확산", "상용화", "판로", "수익", "사업모델", "비즈니스모델", "활용방안"),
        "message": "사업화 목표, 확산 계획, 수익화 근거가 RFP 요약에 없어 내용 확인이 필요합니다.",
    },
    {
        "heading_keywords": ("추진일정", "일정", "로드맵", "추진계획", "마일스톤"),
        "summary_keywords": ("사업기간", "수행기간", "단계별", "로드맵", "마일스톤", "착수", "완료"),
        "message": "세부 일정과 단계별 마일스톤 근거가 RFP 요약에 없어 내용 확인이 필요합니다.",
    },
    {
        "heading_keywords": ("수행체계", "추진체계", "조직", "인력", "투입인력", "역할분담"),
        "summary_keywords": ("인력", "조직", "투입", "전담", "역할", "책임", "수행체계"),
        "message": "투입 인력, 역할 분담, 수행 체계 근거가 RFP 요약에 없어 내용 확인이 필요합니다.",
    },
    {
        "heading_keywords": ("실적", "레퍼런스", "유사사업", "유사실적", "적용사례"),
        "summary_keywords": ("실적", "레퍼런스", "사례", "유사사업", "유사실적"),
        "message": "유사 실적 또는 적용 사례 근거가 RFP 요약에 없어 내용 확인이 필요합니다.",
    },
)


def build_heading_text(section: OutlineSection) -> str:
    label = (section.display_label or "").strip()
    title = section.title.strip()
    if label:
        return f"{label} {title}".strip()
    return title


def normalize_review_text(text: str) -> str:
    normalized = _SYSTEM_REVIEW_PATTERN.sub(r"\1", text.strip())
    return normalized.strip()


def merge_review_texts(*groups: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for item in group:
            normalized = normalize_review_text(item)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            merged.append(normalized)
    return merged


def _normalize_for_match(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def _has_any_keyword(text: str, keywords: tuple[str, ...]) -> bool:
    normalized_text = _normalize_for_match(text)
    return any(_normalize_for_match(keyword) in normalized_text for keyword in keywords)


def strip_inline_review_items(text: str) -> tuple[str, list[str]]:
    kept_lines: list[str] = []
    review_items: list[str] = []

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if SYSTEM_REVIEW_PREFIX in stripped:
            review_text = normalize_review_text(
                stripped[stripped.index(SYSTEM_REVIEW_PREFIX) + len(SYSTEM_REVIEW_PREFIX) :]
            )
            if review_text:
                review_items.append(review_text)
            continue
        kept_lines.append(raw_line)

    cleaned_lines = list(kept_lines)
    while cleaned_lines and not cleaned_lines[0].strip():
        cleaned_lines.pop(0)
    while cleaned_lines and not cleaned_lines[-1].strip():
        cleaned_lines.pop()

    return "\n".join(cleaned_lines).strip(), merge_review_texts(review_items)


def infer_fallback_review_items(
    *,
    section_heading_text: str,
    summary_text: str,
) -> list[str]:
    inferred_items: list[str] = []
    for rule in FALLBACK_REVIEW_RULES:
        if not _has_any_keyword(section_heading_text, rule["heading_keywords"]):
            continue
        if _has_any_keyword(summary_text, rule["summary_keywords"]):
            continue
        inferred_items.append(rule["message"])
    return merge_review_texts(inferred_items)


def build_review_items_for_section(
    *,
    outline_section_id: int | None = None,
    section_heading_text: str,
    item_texts: list[str],
    category: str = "missing_evidence",
    severity: str = "medium",
    source_agent: str = "reviewer",
) -> list[ReviewItemPayload]:
    return [
        ReviewItemPayload(
            outline_section_id=outline_section_id,
            section_heading_text=section_heading_text,
            question_text=item_text,
            category=category,
            severity=severity,
            source_agent=source_agent,
        )
        for item_text in merge_review_texts(item_texts)
    ]


def merge_review_payloads(*groups: list[ReviewItemPayload]) -> list[ReviewItemPayload]:
    merged: list[ReviewItemPayload] = []
    seen: set[tuple[str, str, str]] = set()
    for group in groups:
        for item in group:
            normalized_text = normalize_review_text(item.question_text)
            key = (
                (item.section_heading_text or "").strip(),
                normalized_text,
                (item.category or "").strip(),
            )
            if not normalized_text or key in seen:
                continue
            seen.add(key)
            merged.append(
                ReviewItemPayload(
                    outline_section_id=item.outline_section_id,
                    section_heading_text=item.section_heading_text.strip(),
                    question_text=normalized_text,
                    category=item.category.strip() or "missing_evidence",
                    severity=item.severity.strip() or "medium",
                    source_agent=item.source_agent.strip() or "reviewer",
                )
            )
    return merged


def locate_heading_for_offset(
    *,
    content: str,
    sections: list[OutlineSection],
    offset: int | None,
) -> str | None:
    if offset is None or offset < 0 or not sections:
        return None

    heading_positions: list[tuple[int, str]] = []
    line_offsets = [0]
    for raw_line in content.splitlines(keepends=True):
        line_offsets.append(line_offsets[-1] + len(raw_line))

    normalized_lines = content.splitlines()
    section_index = 0
    for line_index, line in enumerate(normalized_lines):
        if section_index >= len(sections):
            break
        heading_text = build_heading_text(sections[section_index])
        if line.strip() != heading_text:
            continue
        heading_positions.append((line_offsets[line_index], heading_text))
        section_index += 1

    if not heading_positions:
        return None

    current_heading = heading_positions[0][1]
    for position, heading_text in heading_positions:
        if position > offset:
            break
        current_heading = heading_text
    return current_heading
