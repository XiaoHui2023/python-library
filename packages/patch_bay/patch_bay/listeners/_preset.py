from __future__ import annotations

import logging
from typing import Any

try:
    from rich.console import Console
    from rich.markup import escape as _escape_markup

    _RICH = True
except ImportError:
    _RICH = False
    Console = None  # type: ignore[misc, assignment]

    def _escape_markup(s: str) -> str:
        return s.replace("[", "\\[")


_console: Any = None
if _RICH:
    _console = Console(stderr=True, highlight=False)


def _esc(s: object) -> str:
    return _escape_markup(str(s))


def _bytes_hint(b: bytes) -> str:
    n = len(b)
    if n == 0:
        return "空"
    return f"{n} 字节"


def _notify(log: logging.Logger, plain: str, *, rich: str | None = None) -> None:
    """有 Rich 时只走 Rich 打一行；否则 ``logging`` 记一条（人话、单行，不打两次）。"""
    if _RICH and _console is not None and rich:
        try:
            _console.print(rich)
            return
        except Exception:
            pass
    log.info(plain)
