from __future__ import annotations

import json
import logging
import re
from typing import Any

import msgpack

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


def _single_line_for_log(s: str) -> str:
    return re.sub(r"[\r\n]+", " ↵ ", s).strip()


def _is_mostly_printable_text(s: str) -> bool:
    if "\x00" in s:
        return False
    if not s:
        return True
    ok = sum(1 for c in s if c.isprintable() or c in "\n\r\t")
    return ok / len(s) >= 0.88


def _payload_preview(
    b: bytes,
    *,
    max_chars: int = 320,
    max_hex_bytes: int = 56,
) -> str:
    """可读地摘要 payload：优先 JSON（UTF-8 文本）→ Jack 应用层 msgpack → UTF-8 文本 → 十六进制。"""
    if not b:
        return "（空）"
    # JSON（UTF-8）
    try:
        text = b.decode("utf-8")
        t = text.strip()
        if t and t[0] in "[{":
            obj = json.loads(text)
            out = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
            out = _single_line_for_log(out)
            if len(out) > max_chars:
                return out[: max_chars - 1] + "…"
            return out
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        pass
    # Jack ``send`` 应用层：msgpack 编码的字典/模型等
    try:
        obj = msgpack.unpackb(b, raw=False, strict_map_key=False)
        out = json.dumps(obj, ensure_ascii=False, default=str, separators=(",", ":"))
        out = _single_line_for_log(out)
        if len(out) > max_chars:
            return out[: max_chars - 1] + "…"
        return out
    except Exception:
        pass
    # UTF-8 文本
    try:
        text = b.decode("utf-8")
        if _is_mostly_printable_text(text):
            out = _single_line_for_log(text)
            if len(out) > max_chars:
                return out[: max_chars - 1] + "…"
            return out
    except UnicodeDecodeError:
        pass
    # 十六进制（不强调总字节数，除非被截断）
    show = b[:max_hex_bytes]
    hx = " ".join(f"{x:02x}" for x in show)
    if len(b) > max_hex_bytes:
        return f"[二进制] {hx} …（余 {len(b) - max_hex_bytes} 字节）"
    return f"[二进制] {hx}"


def _notify(log: logging.Logger, plain: str, *, rich: str | None = None) -> None:
    """有 Rich 时只走 Rich 打一行；否则 ``logging`` 记一条（人话、单行，不打两次）。"""
    if _RICH and _console is not None and rich:
        try:
            _console.print(rich)
            return
        except Exception:
            pass
    log.info(plain)
