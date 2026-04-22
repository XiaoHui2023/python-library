from __future__ import annotations


class JackListener:
    """接入点生命周期与收发包事件的同步观察点基类。

    子类按需覆盖钩子即可；未覆盖的钩子为空操作。回调须保持轻量，耗时工作请自行
    调度到任务或线程池。
    """

    def on_listen_started(self, listen_address: str) -> None:
        """本机监听已成功启动（此时未必已有交换节点接入）。

        Args:
            listen_address: 可写入交换侧配置的监听地址文本。
        """

    def on_link_up(self) -> None:
        """与至少一个交换节点之间的长连接已就绪，可收发有线帧。"""

    def on_link_down(self) -> None:
        """与某一交换节点之间的链路已结束（可能随后重连或进程退出）。"""

    def on_stopping(self) -> None:
        """即将关闭监听并清理连接，资源回收开始前触发。"""

    def on_incoming_deliver(self, payload: bytes) -> None:
        """收到对端经交换投递而来的应用层二进制块（在用户处理器之前触发）。

        Args:
            payload: 仍为编码后的字节，尚未按业务类型还原。
        """

    def on_send_dropped(self, reason: str) -> None:
        """本机发出的业务帧未离开本节点（例如当前无交换侧连接）。

        Args:
            reason: 机器可读的丢弃原因标识。
        """

    def on_send_failed(self) -> None:
        """链路仍存在但向交换侧发送失败（例如对端已半关闭）。"""

    def on_patchbay_error(self, message: str) -> None:
        """收到交换侧给出的错误说明文本。

        Args:
            message: UTF-8 解码后的简短错误信息。
        """

    def on_ack(self, seq: int) -> None:
        """交换侧确认已收到带序号的发送帧。

        Args:
            seq: 与发送时分配的单调序号一致。
        """
