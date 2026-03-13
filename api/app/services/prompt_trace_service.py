from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, UTC
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.core.config import get_settings

MAX_PROJECT_TRACE_FILES = 200


def _project_trace_dir(project_id: int) -> Path:
    settings = get_settings()
    directory = settings.app_data_dir / "debug" / f"project_{project_id}" / "prompt_traces"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _json_ready(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value


def _prune_old_traces(directory: Path) -> None:
    trace_files = sorted(directory.glob("*.json"))
    for old_file in trace_files[:-MAX_PROJECT_TRACE_FILES]:
        old_file.unlink(missing_ok=True)


def record_prompt_trace(
    *,
    project_id: int,
    trace_kind: str,
    model: str,
    system_prompt: str | None = None,
    user_prompt: str | None = None,
    input_text: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> str:
    trace_id = f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}_{uuid4().hex[:8]}"
    payload = {
        "id": trace_id,
        "project_id": project_id,
        "trace_kind": trace_kind,
        "model": model,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "input_text": input_text,
        "metadata": _json_ready(dict(metadata or {})),
        "created_at": datetime.now(UTC).isoformat(),
    }

    directory = _project_trace_dir(project_id)
    trace_path = directory / f"{trace_id}.json"
    trace_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _prune_old_traces(directory)
    return trace_id


def list_prompt_traces(*, project_id: int, limit: int = 100) -> list[dict[str, Any]]:
    directory = _project_trace_dir(project_id)
    trace_files = sorted(directory.glob("*.json"), reverse=True)[: max(1, limit)]
    traces: list[dict[str, Any]] = []
    for trace_file in trace_files:
        try:
            traces.append(json.loads(trace_file.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return traces
