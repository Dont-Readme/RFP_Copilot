from __future__ import annotations

import re

from app.models.outline import OutlineSection


def build_outline_from_sections(sections: list[OutlineSection]) -> list[dict]:
    return [
        {
            "id": section.id,
            "sort_order": section.sort_order,
            "depth": section.depth,
            "display_label": section.display_label,
            "title": section.title,
        }
        for section in sections
    ]


def outline_title_tokens(title: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[A-Za-z0-9가-힣]+", title.lower())
        if len(token) >= 2
    }
