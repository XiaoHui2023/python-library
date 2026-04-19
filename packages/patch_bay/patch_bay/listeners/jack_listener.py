from __future__ import annotations


class JackListener:
    """可被子类扩展：按需覆盖回调；未覆盖的方法不执行任何操作。

    回调均为同步函数；若在回调中做耗时或异步工作，请自行 ``asyncio.create_task`` 或投递到线程池。
    """

    def on_link_up(self) -> None:
        """已与 PatchBay 建立链路并完成握手，可收发。"""

    def on_link_down(self) -> None:
        """当前链路已结束（将重试挂入或进程已关闭）。"""

    def on_stopping(self) -> None:
        """即将执行 ``aclose`` 清理。"""

    def on_incoming_deliver(self, payload: bytes) -> None:
        """收到一帧 ``deliver``；在通过 ``register`` 注册的回调之前调用。"""

    def on_send_dropped(self, reason: str) -> None:
        """本帧未发出，例如 ``not_connected``。"""

    def on_send_failed(self) -> None:
        """链路仍在但发送失败。"""

    def on_patchbay_error(self, message: str) -> None:
        """收到 PatchBay 的 ``error`` 帧。"""

    def on_ack(self, seq: int) -> None:
        """收到对某次 ``send`` 的确认。"""
