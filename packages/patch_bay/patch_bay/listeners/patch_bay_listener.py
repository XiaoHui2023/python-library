from __future__ import annotations

from collections.abc import Sequence


class PatchBayListener:
    """可被子类扩展：按需覆盖回调；未覆盖的方法不执行任何操作。

    回调均为同步函数；若在回调中做耗时或异步工作，请自行 ``asyncio.create_task`` 或投递到线程池。
    """

    def on_listen_started(self, host: str, port: int) -> None:
        """保留；当前 PatchBay 不向 Jack 提供入站端口，一般不会触发。"""

    def on_listen_stopping(self) -> None:
        """即将停止监听并清理资源。"""

    def on_jacks_dial_plan(self, jacks: Sequence[tuple[str, str]]) -> None:
        """已从配置加载：将按 ``(name, address)`` 主动连接各 Jack 的监听地址。"""

    def on_jack_connected(self, jack_name: str, remote: str | None) -> None:
        """某 Jack WebSocket 握手成功并登记。"""

    def on_jack_disconnected(self, jack_name: str) -> None:
        """某 Jack 从交换侧下线（接入已结束）。"""

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
        detail: str | None = None,
    ) -> None:
        """本条线未投递：``reason`` 为 ``rule`` / ``offline`` / ``patch``；补丁失败（缺键、类型不一致等）时 ``detail`` 为原因。"""

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
