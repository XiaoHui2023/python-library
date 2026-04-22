from __future__ import annotations

import json
import logging
import re
from typing import Any, Literal

import msgpack

try:
    from rich.console import Console
    from rich.markup import escape as _escape_markup

    _RICH = True
except ImportError:
    _RICH = False
    Console = None  # type: ignore[misc, assignment]

    def _escape_markup(s: str) -> str:
        """在无 Rich 时弱化方括号，避免被误当作标记语法。

        Args:
            s: 原始文本。

        Returns:
            转义后可安全拼接进普通日志的字符串。
        """
        return s.replace("[", "\\[")


_console: Any = None
if _RICH:
    _console = Console(stderr=True, highlight=False)


def _esc(s: object) -> str:
    """将任意对象转成适合彩色控制台标记的转义文本。

    Args:
        s: 日志中要内嵌展示的值。

    Returns:
        经彩色扩展或回退规则转义后的字符串。
    """
    return _escape_markup(str(s))


def _single_line_for_log(s: str) -> str:
    """把换行折叠为可见占位，便于单行日志阅读。

    Args:
        s: 可能含换行的文本。

    Returns:
        折叠空白后的单行字符串。
    """
    return re.sub(r"[\r\n]+", " ↵ ", s).strip()


def _is_mostly_printable_text(s: str) -> bool:
    """判断字符串是否大体为人类可读文本（排除含空字节等明显二进制）。

    Args:
        s: 已按 UTF-8 解码的候选文本。

    Returns:
        若可打印字符占比足够高则为真。
    """

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
    """在常规日志级别下生成二进制载荷的短摘要。

    依次尝试：JSON 文本、应用层 msgpack、可打印 UTF-8，最后退回十六进制片段。

    Args:
        b: 原始二进制载荷。
        max_chars: 文本化结果允许的最大字符数（超出则截断）。
        max_hex_bytes: 十六进制展示时最多展示的字节数。

    Returns:
        适合插入单行日志的人类可读摘要。
    """
    if not b:
        return "（空）"
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
    try:
        obj = msgpack.unpackb(b, raw=False, strict_map_key=False)
        out = json.dumps(obj, ensure_ascii=False, default=str, separators=(",", ":"))
        out = _single_line_for_log(out)
        if len(out) > max_chars:
            return out[: max_chars - 1] + "…"
        return out
    except Exception:
        pass
    try:
        text = b.decode("utf-8")
        if _is_mostly_printable_text(text):
            out = _single_line_for_log(text)
            if len(out) > max_chars:
                return out[: max_chars - 1] + "…"
            return out
    except UnicodeDecodeError:
        pass
    show = b[:max_hex_bytes]
    hx = " ".join(f"{x:02x}" for x in show)
    if len(b) > max_hex_bytes:
        return f"[二进制] {hx} …（余 {len(b) - max_hex_bytes} 字节）"
    return f"[二进制] {hx}"


def _payload_preview_full(b: bytes) -> str:
    """在调试级别下尽量完整地展示载荷（结构化则美化，否则全长十六进制）。

    Args:
        b: 原始二进制载荷。

    Returns:
        可能多行的展示文本。
    """
    if not b:
        return "（空）"
    try:
        text = b.decode("utf-8")
        t = text.strip()
        if t and t[0] in "[{":
            obj = json.loads(text)
            return json.dumps(obj, ensure_ascii=False, indent=2)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        pass
    try:
        obj = msgpack.unpackb(b, raw=False, strict_map_key=False)
        return json.dumps(obj, ensure_ascii=False, default=str, indent=2)
    except Exception:
        pass
    try:
        text = b.decode("utf-8")
        if _is_mostly_printable_text(text):
            return text
    except UnicodeDecodeError:
        pass
    return "[二进制] " + " ".join(f"{x:02x}" for x in b)


ListenerLogLevel = Literal["info", "debug"]


def _payload_for_level(b: bytes, level: ListenerLogLevel) -> str:
    """按日志详细程度选择摘要或完整展示策略。

    Args:
        b: 原始二进制载荷。
        level: 信息或调试。

    Returns:
        对应级别的可读文本。
    """
    if level == "debug":
        return _payload_preview_full(b)
    return _payload_preview(b)


def _notify(log: logging.Logger, plain: str, *, rich: str | None = None) -> None:
    """优先走彩色控制台单行输出；不可用时退回标准库日志。

    Args:
        log: 标准库记录器，在彩色路径不可用时写入信息级别记录。
        plain: 彩色路径不可用或失败时写入的纯文本。
        rich: 可选的带标记彩色文本；为空时只走纯文本路径。

    Returns:
        无。
    """
    if _RICH and _console is not None and rich:
        try:
            _console.print(rich)
            return
        except Exception:
            pass
    log.info(plain)
