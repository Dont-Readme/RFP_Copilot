from __future__ import annotations

import re


def _tokenize(value: str) -> set[str]:
    raw_tokens = re.findall(r"[A-Za-z0-9가-힣]+", value.lower())
    return {token for token in raw_tokens if len(token) >= 2}


def split_draft_sections(content_md: str) -> list[dict[str, str]]:
    sections: list[dict[str, str]] = []
    current_title = "전체 초안"
    current_lines: list[str] = []

    for line in content_md.splitlines():
        if line.startswith("## "):
            if current_lines:
                sections.append({"title": current_title, "content": "\n".join(current_lines).strip()})
            current_title = line.removeprefix("## ").strip()
            current_lines = []
            continue
        current_lines.append(line)

    if current_lines:
        sections.append({"title": current_title, "content": "\n".join(current_lines).strip()})

    return sections or [{"title": "전체 초안", "content": content_md}]


def build_mapping_results(
    *,
    draft_section_id: int,
    draft_content: str,
    evaluation_items: list[dict],
) -> tuple[list[dict], list[dict]]:
    sections = split_draft_sections(draft_content)
    mappings: list[dict] = []
    warnings: list[dict] = []

    for item in evaluation_items:
        item_tokens = _tokenize(f"{item['title']} {item.get('description', '')}")
        best_section: dict[str, str] | None = None
        best_score = 0.0

        for section in sections:
            section_tokens = _tokenize(f"{section['title']} {section['content']}")
            if not item_tokens:
                score = 0.0
            else:
                overlap = item_tokens & section_tokens
                score = len(overlap) / len(item_tokens)
            if score > best_score:
                best_score = score
                best_section = section

        if best_score >= 0.35:
            label = "strong"
        elif best_score >= 0.12:
            label = "weak"
        else:
            label = "missing"

        mappings.append(
            {
                "evaluation_item_id": item["id"],
                "draft_section_id": draft_section_id if best_section else None,
                "section_title": best_section["title"] if best_section else None,
                "strength_score": round(best_score, 3),
                "strength_label": label,
                "rationale_text": (
                    f"'{item['title']}'와 가장 많이 겹치는 섹션은 "
                    f"'{best_section['title'] if best_section else '없음'}' 입니다."
                ),
            }
        )

        if label == "missing":
            warnings.append(
                {
                    "type": "missing",
                    "evaluation_item_id": item["id"],
                    "draft_section_id": None,
                    "message": f"평가항목 '{item['title']}'에 대응하는 문단이 부족합니다.",
                }
            )
        elif label == "weak":
            warnings.append(
                {
                    "type": "weak",
                    "evaluation_item_id": item["id"],
                    "draft_section_id": draft_section_id,
                    "message": f"평가항목 '{item['title']}'의 근거를 더 직접적으로 보강하세요.",
                }
            )

    return mappings, warnings
