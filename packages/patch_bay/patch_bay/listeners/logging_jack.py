from __future__ import annotations

import logging

from .jack_listener import JackListener
from ._preset import _RICH, _bytes_hint, _esc, _notify


def _drop_reason_zh(reason: str) -> str:
    if reason == "not_connected":
        return "还没连上交换机"
    return reason


class LoggingJackListener(JackListener):
    """事件用人话单行输出：装了 Rich 就用 Rich，否则用 logging。"""

    def __init__(self, *, logger: logging.Logger | None = None) -> None:
        self._log = logger or logging.getLogger("patch_bay.events.jack")

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
        sz = _bytes_hint(payload)
        plain = f"收到对方发来的数据（{sz}）。"
        rich = f"[cyan]📨[/] 收到对方数据 [dim]（{sz}）[/]。"
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
        plain = f"刚才发的数据交换机已确认（序号 {seq}）。"
        rich = f"[dim]✅[/] 已确认  [yellow]#{seq}[/]"
        _notify(self._log, plain, rich=rich if _RICH else None)
