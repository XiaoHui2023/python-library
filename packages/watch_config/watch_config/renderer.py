from __future__ import annotations

import sys
import logging
from pprint import pformat
from typing import Any
from .changelog import ChangeLog, ChangeType
from abc import ABC, abstractmethod

class ChangeRenderer(ABC):
    @abstractmethod
    def render(self, changelog: ChangeLog) -> str: ...

    def emit(self, changelog: ChangeLog, logger: logging.Logger) -> None:
        text = self.render(changelog)
        if text:
            logger.info(text)


class DefaultRenderer(ChangeRenderer):
    _ICONS = {
        ChangeType.ADDED: "+",
        ChangeType.REMOVED: "-",
        ChangeType.UPDATED: "~",
        ChangeType.TYPE_CHANGED: "!",
    }

    _COLORS = {
        ChangeType.ADDED: "\033[32m",
        ChangeType.REMOVED: "\033[31m",
        ChangeType.UPDATED: "\033[33m",
        ChangeType.TYPE_CHANGED: "\033[35m",
    }

    _RESET = "\033[0m"
    _BOLD = "\033[1m"
    _DIM = "\033[2m"

    def __init__(self, *, color: bool | None = None, max_value_length: int = 120) -> None:
        if color is None:
            color = sys.stderr.isatty()
        self.color = color
        self.max_value_length = max_value_length

    def render(self, changelog: ChangeLog) -> str:
        if changelog.is_empty:
            return ""

        title = self._style(
            f"Config Changes ({len(changelog.entries)}):",
            self._BOLD,
        )
        lines = [title]

        for entry in changelog.entries:
            icon = self._ICONS[entry.type]
            color = self._COLORS[entry.type]
            path = entry.path.removeprefix("$.").removeprefix("$")
            lines.append(self._style(f"{icon} {path}", color))

            if entry.type == ChangeType.ADDED:
                lines.append(self._style(f"  + {self._pretty(entry.new_value)}", self._COLORS[ChangeType.ADDED]))
            elif entry.type == ChangeType.REMOVED:
                lines.append(self._style(f"  - {self._pretty(entry.old_value)}", self._COLORS[ChangeType.REMOVED]))
            else:
                lines.append(self._style(f"  - {self._pretty(entry.old_value)}", self._COLORS[ChangeType.REMOVED]))
                lines.append(self._style(f"  + {self._pretty(entry.new_value)}", self._COLORS[ChangeType.ADDED]))

        return "\n".join(lines)

    def _pretty(self, value: Any) -> str:
        text = pformat(value, compact=True, sort_dicts=False, width=88)
        if len(text) <= self.max_value_length:
            return text
        return text[: self.max_value_length - 3] + "..."

    def _style(self, text: str, code: str) -> str:
        if not self.color:
            return text
        return f"{code}{text}{self._RESET}"

    def _dim(self, text: str) -> str:
        return self._style(text, self._DIM)