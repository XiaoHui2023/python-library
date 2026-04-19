from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class PatchBayListener:
    """可被子类扩展：按需覆盖回调；未覆盖的方法不执行任何操作。

    回调均为同步函数；若在回调中做耗时或异步工作，请自行 ``asyncio.create_task`` 或投递到线程池。
    """

    def on_listen_started(self, host: str, port: int) -> None:
        """PatchBay 已在 ``host:port`` 上开始接受连接（``port`` 为解析后的监听端口）。"""

    def on_listen_stopping(self) -> None:
        """即将停止监听并清理资源。"""

    def on_jack_connected(self, jack_name: str, remote: str | None) -> None:
        """某 Jack WebSocket 握手成功并登记。"""

    def on_jack_disconnected(self, jack_name: str) -> None:
        """某 Jack 连接已移除。"""

    def on_incoming_send(
        self, from_jack: str, payload: bytes, seq: int | None
    ) -> None:
        """收到来自某 Jack 的一帧 ``send``（尚未做规则过滤）。"""

    def on_route_skipped(
        self,
        from_jack: str,
        to_jack: str,
        payload: bytes,
        *,
        reason: str,
    ) -> None:
        """本条线未投递：``reason`` 为 ``rule``（规则未通过）或 ``offline``（对端未连接）。"""

    def on_packet_delivered(self, from_jack: str, to_jack: str, payload: bytes) -> None:
        """已成功向对方 Jack 发出 ``deliver`` 帧。"""

    def on_deliver_failed(
        self,
        from_jack: str,
        to_jack: str,
        payload: bytes,
        error: BaseException | None,
    ) -> None:
        """向对方发送失败（例如对端已断）。"""


def emit_listeners(
    listeners: list[PatchBayListener],
    method: str,
    *args: Any,
    **kwargs: Any,
) -> None:
    """调用每个 listener 上名为 ``method`` 的可调用（若存在且可调用）。"""
    for lst in listeners:
        fn = getattr(lst, method, None)
        if not callable(fn):
            continue
        try:
            fn(*args, **kwargs)
        except Exception:
            logger.exception("listener %s.%s failed", type(lst).__name__, method)
