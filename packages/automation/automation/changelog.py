"""配置变更记录与格式化输出"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ChangeType(StrEnum):
    ADDED = "added"
    REMOVED = "removed"
    UPDATED = "updated"
    REVALIDATED = "revalidated"


_ICONS = {
    ChangeType.ADDED: "+",
    ChangeType.REMOVED: "-",
    ChangeType.UPDATED: "~",
    ChangeType.REVALIDATED: "!",
}

_COLORS = {
    ChangeType.ADDED: "\033[32m",
    ChangeType.REMOVED: "\033[31m",
    ChangeType.UPDATED: "\033[33m",
    ChangeType.REVALIDATED: "\033[36m",
}

_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"


@dataclass
class ChangeEntry:
    type: ChangeType
    section: str
    name: str
    field_diffs: dict[str, tuple[Any, Any]] = field(default_factory=dict)


@dataclass
class ChangeLog:
    entries: list[ChangeEntry] = field(default_factory=list)

    def added(self, section: str, name: str) -> None:
        self.entries.append(ChangeEntry(ChangeType.ADDED, section, name))

    def removed(self, section: str, name: str) -> None:
        self.entries.append(ChangeEntry(ChangeType.REMOVED, section, name))

    def updated(
        self, section: str, name: str, diffs: dict[str, tuple[Any, Any]]
    ) -> None:
        self.entries.append(ChangeEntry(ChangeType.UPDATED, section, name, diffs))

    def revalidated(self, section: str, name: str) -> None:
        self.entries.append(ChangeEntry(ChangeType.REVALIDATED, section, name))

    @property
    def is_empty(self) -> bool:
        return len(self.entries) == 0

    def format(self, *, color: bool = True) -> str:
        if not self.entries:
            return "No changes."

        lines: list[str] = []
        bar = f"{_BOLD}{'─' * 48}{_RESET}" if color else "─" * 48
        title = f"Configuration Changes ({len(self.entries)})"

        lines.append(bar)
        lines.append(f"  {_BOLD}{title}{_RESET}" if color else f"  {title}")
        lines.append(bar)

        by_section: dict[str, list[ChangeEntry]] = {}
        for entry in self.entries:
            by_section.setdefault(entry.section, []).append(entry)

        for section, entries in by_section.items():
            lines.append("")
            header = f"  [{section}]"
            lines.append(f"{_BOLD}{header}{_RESET}" if color else header)

            for entry in entries:
                icon = _ICONS[entry.type]
                if color:
                    c = _COLORS[entry.type]
                    lines.append(f"    {c}{icon} {entry.name}{_RESET}")
                else:
                    lines.append(f"    {icon} {entry.name}")

                for fname, (old_val, new_val) in entry.field_diffs.items():
                    diff_line = f"      {fname}: {old_val!r} → {new_val!r}"
                    lines.append(
                        f"      {_DIM}{fname}: {old_val!r} → {new_val!r}{_RESET}"
                        if color
                        else diff_line
                    )

        lines.append("")
        lines.append(bar)
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.format(color=False)

    def __repr__(self) -> str:
        return f"ChangeLog(entries={len(self.entries)})"