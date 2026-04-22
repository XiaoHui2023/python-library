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
    """将内部丢弃原因码转写为面向中文读者的短说明。

    Args:
        reason: 监听器协议中的原因字符串。

    Returns:
        用于日志展示的本地化短语。
    """
    if reason == "not_connected":
        return "还没连上交换机"
    return reason


class LoggingJackListener(JackListener):
    """把接入点事件写成人类可读的单行日志；若环境提供彩色控制台扩展则优先用它输出。"""

    def __init__(
        self,
        *,
        logger: logging.Logger | None = None,
        level: ListenerLogLevel = "info",
    ) -> None:
        """绑定日志记录器与详细程度。

        Args:
            logger: 目标记录器；缺省使用本包命名空间下的默认记录器。
            level: 信息级别侧重步骤与载荷摘要；调试级别额外包含确认等细节。
        """
        self._log = logger or logging.getLogger("patch_jack.events.jack")
        self._level: ListenerLogLevel = level

    def _pv(self, payload: bytes) -> str:
        """按当前详细程度生成载荷的可读摘要。

        Args:
            payload: 原始应用层字节块。

        Returns:
            适合插入单行消息的短文本。
        """
        return _payload_for_level(payload, self._level)

    def on_listen_started(self, listen_address: str) -> None:
        """输出监听已就绪的提示。

        Args:
            listen_address: 本机对外可宣告的监听地址。
        """
        plain = f"在本机监听 {listen_address}，等交换节点接入。"
        rich = (
            f"[bold cyan]📡[/] 在本机 [green]{_esc(listen_address)}[/] 监听，等交换节点接入。"
        )
        _notify(self._log, plain, rich=rich if _RICH else None)

    def on_link_up(self) -> None:
        """输出与交换侧建链成功的提示。"""
        plain = "连上交换机了。"
        rich = "[bold green]🔗[/] 连上交换机了。"
        _notify(self._log, plain, rich=rich if _RICH else None)

    def on_link_down(self) -> None:
        """输出与交换侧断开的提示。"""
        plain = "和交换机断开了。"
        rich = "[yellow]🔓[/] 和交换机断开了。"
        _notify(self._log, plain, rich=rich if _RICH else None)

    def on_stopping(self) -> None:
        """输出即将关闭的提示。"""
        plain = "正在退出。"
        rich = "[red]🛑[/] 正在退出。"
        _notify(self._log, plain, rich=rich if _RICH else None)

    def on_incoming_deliver(self, payload: bytes) -> None:
        """输出来自对端、经交换投递的数据摘要。

        Args:
            payload: 应用层原始字节块。
        """
        body = self._pv(payload)
        plain = f"收到对方数据：{body}"
        rich = f"[cyan]📨[/] {_esc(body)}"
        _notify(self._log, plain, rich=rich if _RICH else None)

    def on_send_dropped(self, reason: str) -> None:
        """输出未发出帧的原因说明。

        Args:
            reason: 丢弃原因的内部标识。
        """
        why = _drop_reason_zh(reason)
        plain = f"这条没发出去：{why}。"
        rich = f"[yellow]⚠️[/] 没发出去  [magenta]{_esc(why)}[/]。"
        _notify(self._log, plain, rich=rich if _RICH else None)

    def on_send_failed(self) -> None:
        """输出发送失败提示。"""
        plain = "发送失败了。"
        rich = "[red]❌[/] 发送失败。"
        _notify(self._log, plain, rich=rich if _RICH else None)

    def on_patchbay_error(self, message: str) -> None:
        """输出交换侧错误文本。

        Args:
            message: 错误说明字符串。
        """
        plain = f"交换机那边报错：{message}"
        rich = f"[red]⛔[/] 交换机： [red]{_esc(message)}[/]"
        _notify(self._log, plain, rich=rich if _RICH else None)

    def on_ack(self, seq: int) -> None:
        """在调试级别下输出已确认的序号。

        Args:
            seq: 被确认的发送序号。
        """
        if self._level != "debug":
            return
        plain = f"交换机已确认 seq={seq}。"
        rich = f"[dim]✅[/] 已确认 [yellow]seq={seq}[/]"
        _notify(self._log, plain, rich=rich if _RICH else None)
