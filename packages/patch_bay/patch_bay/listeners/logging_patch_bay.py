from __future__ import annotations

import logging

from .patch_bay_listener import PatchBayListener
from ._preset import _RICH, _bytes_hint, _esc, _notify


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
        self, from_jack: str, payload: bytes, seq: int | None
    ) -> None:
        sz = _bytes_hint(payload)
        if seq is not None:
            plain = f"收到「{from_jack}」发来的数据（{sz}），序号 {seq}。"
        else:
            plain = f"收到「{from_jack}」发来的数据（{sz}）。"
        rich = (
            f"[blue]📥[/] 收到 [bold]{_esc(from_jack)}[/] 的数据 [dim]（{sz}）[/]"
            + (f"  [yellow]#{seq}[/]" if seq is not None else "")
            + "。"
        )
        _notify(self._log, plain, rich=rich if _RICH else None)

    def on_route_skipped(
        self,
        from_jack: str,
        to_jack: str,
        payload: bytes,
        *,
        reason: str,
    ) -> None:
        sz = _bytes_hint(payload)
        reason_zh = "对端没接上" if reason == "offline" else ("规则没过" if reason == "rule" else reason)
        plain = f"没把「{from_jack}」的消息转给「{to_jack}」：{reason_zh}（包 {sz}）。"
        rich = (
            f"[yellow]⏭️[/] 未转发 [bold]{_esc(from_jack)}[/]→[bold]{_esc(to_jack)}[/]  "
            f"[magenta]{_esc(reason_zh)}[/]  [dim]（{sz}）[/]。"
        )
        _notify(self._log, plain, rich=rich if _RICH else None)

    def on_packet_delivered(self, from_jack: str, to_jack: str, payload: bytes) -> None:
        sz = _bytes_hint(payload)
        plain = f"已从「{from_jack}」转发到「{to_jack}」（{sz}）。"
        rich = (
            f"[green]📤[/] [bold]{_esc(from_jack)}[/] → [bold]{_esc(to_jack)}[/]  [dim]（{sz}）[/]。"
        )
        _notify(self._log, plain, rich=rich if _RICH else None)

    def on_deliver_failed(
        self,
        from_jack: str,
        to_jack: str,
        payload: bytes,
        error: BaseException | None,
    ) -> None:
        sz = _bytes_hint(payload)
        err = str(error) if error else "未知原因"
        plain = f"发给「{to_jack}」失败（从「{from_jack}」来，{sz}）：{err}"
        rich = (
            f"[red]❌[/] 发给 [bold]{_esc(to_jack)}[/] 失败  [dim]（{sz}）[/]  [red]{_esc(err)}[/]"
        )
        _notify(self._log, plain, rich=rich if _RICH else None)
