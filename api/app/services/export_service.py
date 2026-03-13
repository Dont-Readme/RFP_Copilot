from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings


def build_preview_markdown(
    *,
    project_name: str,
    draft_content: str,
    questions: list[dict],
    extraction_summary: dict | None,
) -> str:
    lines = [f"# {project_name} Export Preview", ""]

    if extraction_summary:
        lines.extend(
            [
                "## RFP 요약",
                f"- 사업 개요: {extraction_summary.get('project_summary_text', '').strip() or 'TBD'}",
                f"- 요구사항 수: {extraction_summary.get('requirements_count', 0)}",
                f"- 평가항목 수: {extraction_summary.get('evaluation_count', 0)}",
                "",
            ]
        )

    lines.extend(["## Draft", draft_content.strip(), ""])

    if questions:
        lines.append("## 작성 확인 사항")
        lines.extend(
            [
                f"- [{question['status']}] {question.get('section_heading_text', '').strip() or '목차 미상'}: {question['question_text']}"
                for question in questions
            ]
        )
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def create_export_artifacts(
    *,
    project_id: int,
    project_name: str,
    formats: list[str],
    draft_content: str,
    questions: list[dict],
    extraction_summary: dict | None,
) -> tuple[str, str, str]:
    settings = get_settings()
    session_id = uuid4().hex[:12]
    session_dir = settings.export_dir / f"project_{project_id}" / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    preview_md = build_preview_markdown(
        project_name=project_name,
        draft_content=draft_content,
        questions=questions,
        extraction_summary=extraction_summary,
    )

    preview_path = session_dir / "preview.md"
    preview_path.write_text(preview_md, encoding="utf-8")

    files: dict[str, str] = {"md": str(preview_path.relative_to(settings.app_data_dir))}

    if "txt" in formats:
        txt_path = session_dir / "preview.txt"
        txt_path.write_text(preview_md, encoding="utf-8")
        files["txt"] = str(txt_path.relative_to(settings.app_data_dir))
    return session_id, str(preview_path.relative_to(settings.app_data_dir)), json.dumps(files)
