from __future__ import annotations

from pathlib import Path


class LocalStorageProvider:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir

    def ensure(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
