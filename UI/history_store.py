from __future__ import annotations

import json
from pathlib import Path


class HistoryStore:
    """Persist and read check history records."""

    def __init__(self, history_path: Path, max_records: int = 500) -> None:
        self.history_path = history_path
        self.max_records = max(1, int(max_records))

    def load_entries(self) -> list[dict]:
        """Load history records from json file."""
        if not self.history_path.exists():
            return []
        try:
            with self.history_path.open("r", encoding="utf-8") as file:
                raw = json.load(file)
            if not isinstance(raw, list):
                return []
            return [item for item in raw if isinstance(item, dict)]
        except Exception:
            return []

    def append_entries(self, entries: list[dict]) -> None:
        """Append history records and keep max record limit."""
        if len(entries) == 0:
            return
        history = self.load_entries()
        history.extend(entries)
        history = history[-self.max_records :]
        self._save_entries(history)

    def _save_entries(self, entries: list[dict]) -> None:
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        with self.history_path.open("w", encoding="utf-8") as file:
            json.dump(entries, file, ensure_ascii=False, indent=2)
