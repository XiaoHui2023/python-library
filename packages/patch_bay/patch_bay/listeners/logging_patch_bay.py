from __future__ import annotations

import logging

from .patch_bay_listener import PatchBayListener
from ._preset import _RICH, _esc, _notify, _payload_preview


class LoggingPatchBayListener(PatchBayListener):
    """事件用人话单行输出：装了 Rich 就用 Rich，否则用 logging。"""

    def __init__(self, *, logger: logging.Logger | None = None, label: str = "PatchBay") -> None:
        self._log = logger or logging.getLogger("patch_bay.events.patchbay")
        self._label = label

    def on_listen_started(self, host: str, port: int) -> None:
        plain = f"{self._label}已在 {host}:{port} 开始监听，Jack 可以接上。"
        rich = (
            f"[bold cyan]📡[/] [bold]{_esc(self._label)}[/] 已在 "
            f"[green]{_esc(host)}[/]:[yellow]{port}[/] 开始监听，Jack 可以接上。"
        )
        _notify(self._log, plain, rich=rich if _RICH else None)

    def on_listen_stopping(self) -> None:
        plain = f"{self._label}要停止监听了。"
        rich = f"[yellow]🛑[/] [bold]{_esc(self._label)}[/] 要停止监听了。"
        _notify(self._log, plain, rich=rich if _RICH else None)

    def on_jacks_dial_plan(self, jacks: list[tuple[str, str]]) -> None:
        if not jacks:
            plain = f"{self._label} 配置里没有 Jack，不会发起连接。"
            rich = f"[dim]📋[/] [bold]{_esc(self._label)}[/] 配置里没有 Jack。"
            _notify(self._log, plain, rich=rich if _RICH else None)
            return
        parts_plain = [f"「{n}」@{a}" for n, a in jacks]
        plain = f"{self._label} 将连接：{'; '.join(parts_plain)}"
        parts_rich = [f"[bold]{_esc(n)}[/] → [cyan]{_esc(a)}[/]" for n, a in jacks]
        rich = f"[dim]📋[/] [bold]{_esc(self._label)}[/] 将连接：  " + "  ·  ".join(parts_rich)
        _notify(self._log, plain, rich=rich if _RICH else None)

    def on_jack_connected(self, jack_name: str, remote: str | None) -> None:
        tail = f"（来自 {remote}）" if remote else ""
        plain = f"「{jack_name}」接上了。{tail}".strip()
        r = _esc(remote) if remote else ""
        rich = (
            f"[green]🔌[/] [bold]{_esc(jack_name)}[/] 接上了"
            + (f"  [dim]（{r}）[/]" if remote else "")
            + "。"
        )
        _notify(self._log, plain, rich=rich if _RICH else None)

    def on_jack_disconnected(self, jack_name: str) -> None:
        plain = f"「{jack_name}」下线了。"
        rich = f"[dim]👋[/] [bold]{_esc(jack_name)}[/] 下线了。"
        _notify(self._log, plain, rich=rich if _RICH else None)

    def on_incoming_send(
        self, from_jack: str, payload: bytes, _seq: int | None
    ) -> None:
        body = _payload_preview(payload)
        plain = f"收到「{from_jack}」：{body}"
        rich = f"[blue]📥[/] [bold]{_esc(from_jack)}[/] → {_esc(body)}"
        _notify(self._log, plain, rich=rich if _RICH else None)

    def on_route_skipped(
        self,
        from_jack: str,
        to_jack: str,
        payload: bytes,
        *,
        reason: str,
    ) -> None:
        body = _payload_preview(payload)
        reason_zh = "对端没接上" if reason == "offline" else ("规则没过" if reason == "rule" else reason)
        plain = f"没把「{from_jack}」→「{to_jack}」（{reason_zh}）：{body}"
        rich = (
            f"[yellow]⏭️[/] [bold]{_esc(from_jack)}[/]→[bold]{_esc(to_jack)}[/] "
            f"[magenta]{_esc(reason_zh)}[/]  {_esc(body)}"
        )
        _notify(self._log, plain, rich=rich if _RICH else None)

    def on_packet_delivered(self, from_jack: str, to_jack: str, payload: bytes) -> None:
        body = _payload_preview(payload)
        plain = f"已转发「{from_jack}」→「{to_jack}」：{body}"
        rich = f"[green]📤[/] [bold]{_esc(from_jack)}[/] → [bold]{_esc(to_jack)}[/]  {_esc(body)}"
        _notify(self._log, plain, rich=rich if _RICH else None)

    def on_deliver_failed(
        self,
        from_jack: str,
        to_jack: str,
        payload: bytes,
        error: BaseException | None,
    ) -> None:
        body = _payload_preview(payload)
        err = str(error) if error else "未知原因"
        plain = f"发给「{to_jack}」失败（从「{from_jack}」）：{body} 原因：{err}"
        rich = (
            f"[red]❌[/] →[bold]{_esc(to_jack)}[/]  {_esc(body)}  [red]{_esc(err)}[/]"
        )
        _notify(self._log, plain, rich=rich if _RICH else None)
