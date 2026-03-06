from __future__ import annotations


def build_rewrite_suggestion(selected_text: str, instruction: str) -> tuple[str, str]:
    replacement_text = (
        f"{selected_text.strip()}\n\n"
        f"[부분 수정 제안] {instruction.strip()}에 맞춰 근거와 표현을 보강한 초안입니다."
    )
    diff_hint = "선택 구간만 교체하고, 저장 전 문맥 연결을 한 번 검토하세요."
    return replacement_text, diff_hint
