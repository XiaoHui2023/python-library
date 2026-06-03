from __future__ import annotations

import json
from pathlib import Path

from ai_agent.memory.models import (
    DateMemoryDay,
    ImportantMemoryEntry,
    LongTermChunk,
    MemoryMessage,
    MemorySnapshot,
)


class MemoryStore:
    """将会话记忆读写为存储目录下的 JSON 文件。"""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._short_term_path = root / "short_term.json"
        self._date_dir = root / "date"
        self._long_term_path = root / "long_term.json"
        self._important_path = root / "important.json"

    @property
    def root(self) -> Path:
        return self._root

    def ensure_layout(self) -> None:
        self._root.mkdir(parents=True, exist_ok=True)
        self._date_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> MemorySnapshot:
        self.ensure_layout()
        short_term = _read_list(self._short_term_path, MemoryMessage)
        date_days = self._load_date_days()
        long_term = _read_list(self._long_term_path, LongTermChunk)
        important = _read_list(self._important_path, ImportantMemoryEntry)
        return MemorySnapshot(
            short_term=short_term,
            date_days=date_days,
            long_term=long_term,
            important=important,
        )

    def save_short_term(self, messages: list[MemoryMessage]) -> None:
        self.ensure_layout()
        _write_list(self._short_term_path, messages)

    def save_date_day(self, day: DateMemoryDay) -> None:
        self.ensure_layout()
        path = self._date_dir / f"{day.date}.json"
        path.write_text(
            day.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def remove_date_day(self, date_label: str) -> None:
        path = self._date_dir / f"{date_label}.json"
        if path.is_file():
            path.unlink()

    def prune_date_files(self, active_dates: set[str]) -> None:
        if not self._date_dir.is_dir():
            return
        for path in self._date_dir.glob("*.json"):
            if path.stem not in active_dates:
                path.unlink(missing_ok=True)

    def save_long_term(self, chunks: list[LongTermChunk]) -> None:
        self.ensure_layout()
        _write_list(self._long_term_path, chunks)

    def save_important(self, entries: list[ImportantMemoryEntry]) -> None:
        self.ensure_layout()
        _write_list(self._important_path, entries)

    def _load_date_days(self) -> list[DateMemoryDay]:
        if not self._date_dir.is_dir():
            return []
        days: list[DateMemoryDay] = []
        for path in sorted(self._date_dir.glob("*.json")):
            raw = path.read_text(encoding="utf-8")
            if not raw.strip():
                continue
            days.append(DateMemoryDay.model_validate_json(raw))
        return days


def _read_list(path: Path, model: type) -> list:
    if not path.is_file():
        return []
    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        return []
    data = json.loads(raw)
    if not isinstance(data, list):
        return []
    return [model.model_validate(item) for item in data]


def _write_list(path: Path, items: list) -> None:
    payload = [item.model_dump(mode="json") for item in items]
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
