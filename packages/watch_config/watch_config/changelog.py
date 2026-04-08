from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ChangeType(StrEnum):
    ADDED = "added"
    REMOVED = "removed"
    UPDATED = "updated"
    TYPE_CHANGED = "type_changed"


@dataclass(slots=True)
class ChangeEntry:
    type: ChangeType
    path: str
    old_value: Any = None
    new_value: Any = None


@dataclass
class ChangeLog:
    entries: list[ChangeEntry] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.entries

    def added(self, path: str, value: Any) -> None:
        self.entries.append(
            ChangeEntry(
                type=ChangeType.ADDED,
                path=path,
                old_value=None,
                new_value=value,
            )
        )

    def removed(self, path: str, value: Any) -> None:
        self.entries.append(
            ChangeEntry(
                type=ChangeType.REMOVED,
                path=path,
                old_value=value,
                new_value=None,
            )
        )

    def updated(self, path: str, old_value: Any, new_value: Any) -> None:
        self.entries.append(
            ChangeEntry(
                type=ChangeType.UPDATED,
                path=path,
                old_value=old_value,
                new_value=new_value,
            )
        )

    def type_changed(self, path: str, old_value: Any, new_value: Any) -> None:
        self.entries.append(
            ChangeEntry(
                type=ChangeType.TYPE_CHANGED,
                path=path,
                old_value=old_value,
                new_value=new_value,
            )
        )

    def __len__(self) -> int:
        return len(self.entries)

    def __iter__(self):
        return iter(self.entries)