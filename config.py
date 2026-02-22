"""
config.py - Persistent configuration management
"""

from __future__ import annotations

import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".pastamonitor"
CONFIG_FILE = CONFIG_DIR / "config.json"


class ConfigManager:
    """Loads and persists app configuration (monitored folders, etc.)."""

    def __init__(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self._data: dict = self._load()

    # ── Internal ──────────────────────────────────────────────────────────

    def _load(self) -> dict:
        if CONFIG_FILE.exists():
            try:
                return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"folders": []}

    def save(self) -> None:
        CONFIG_FILE.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ── Public API ────────────────────────────────────────────────────────

    @property
    def folders(self) -> list[str]:
        return self._data.setdefault("folders", [])

    def add_folder(self, path: str) -> bool:
        """Add a folder. Returns True if it was new."""
        norm = str(Path(path).resolve())
        if norm not in self.folders:
            self.folders.append(norm)
            self.save()
            return True
        return False

    def remove_folder(self, path: str) -> bool:
        """Remove a folder. Returns True if it existed."""
        norm = str(Path(path).resolve())
        if norm in self.folders:
            self.folders.remove(norm)
            self.save()
            return True
        return False
