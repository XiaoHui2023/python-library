from __future__ import annotations

import logging

from .jack_listener import JackListener
from ._preset import (
    ListenerLogLevel,
    _RICH,
    _esc,
    _notify,
    _payload_for_level,
)


def _drop_reason_zh(reason: str) -> str:
    if reason == "not_connected":
        return "还没连上交换机"
    return reason


class LoggingJackListener(JackListener):
    """事件用人话单行输出：装了 Rich 就用 Rich，否则用 logging。

    ``level``：``info`` 为常用步骤 + 数据包摘要；``debug`` 打印全部事件（含 ack）且数据包尽量完整。
    """

    def __init__(
        self,
        *,
        logger: logging.Logger | None = None,
        level: ListenerLogLevel = "info",
    ) -> None:
        self._log = logger or logging.getLogger("patch_bay.events.jack")
        self._level: ListenerLogLevel = level

    def _pv(self, payload: bytes) -> str:
        return _payload_for_level(payload, self._level)

    def on_listen_started(self, listen_address: str) -> None:
        plain = f"在本机监听 {listen_address}，等 PatchBay 接入。"
        rich = (
            f"[bold cyan]📡[/] 在本机 [green]{_esc(listen_address)}[/] 监听，等 PatchBay 接入。"
        )
        _notify(self._log, plain, rich=rich if _RICH else None)

    def on_link_up(self) -> None:
        plain = "连上交换机了。"
        rich = "[bold green]🔗[/] 连上交换机了。"
        _notify(self._log, plain, rich=rich if _RICH else None)

    def on_link_down(self) -> None:
        plain = "和交换机断开了。"
        rich = "[yellow]🔓[/] 和交换机断开了。"
        _notify(self._log, plain, rich=rich if _RICH else None)

    def on_stopping(self) -> None:
        plain = "正在退出。"
        rich = "[red]🛑[/] 正在退出。"
        _notify(self._log, plain, rich=rich if _RICH else None)

    def on_incoming_deliver(self, payload: bytes) -> None:
        body = self._pv(payload)
        plain = f"收到对方数据：{body}"
        rich = f"[cyan]📨[/] {_esc(body)}"
        _notify(self._log, plain, rich=rich if _RICH else None)

    def on_send_dropped(self, reason: str) -> None:
        why = _drop_reason_zh(reason)
        plain = f"这条没发出去：{why}。"
        rich = f"[yellow]⚠️[/] 没发出去  [magenta]{_esc(why)}[/]。"
        _notify(self._log, plain, rich=rich if _RICH else None)

    def on_send_failed(self) -> None:
        plain = "发送失败了。"
        rich = "[red]❌[/] 发送失败。"
        _notify(self._log, plain, rich=rich if _RICH else None)

    def on_patchbay_error(self, message: str) -> None:
        plain = f"交换机那边报错：{message}"
        rich = f"[red]⛔[/] 交换机： [red]{_esc(message)}[/]"
        _notify(self._log, plain, rich=rich if _RICH else None)

    def on_ack(self, seq: int) -> None:
        if self._level != "debug":
            return
        plain = f"交换机已确认 seq={seq}。"
        rich = f"[dim]✅[/] 已确认 [yellow]seq={seq}[/]"
        _notify(self._log, plain, rich=rich if _RICH else None)
