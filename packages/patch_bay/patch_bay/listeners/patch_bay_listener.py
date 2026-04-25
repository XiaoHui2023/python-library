from __future__ import annotations

from collections.abc import Sequence


class PatchBayListener:
    """PatchBay 运行事件监听器基类。

    子类按需覆盖关心的同步回调；未覆盖的方法不执行任何操作。
    """

    def on_listen_started(self, host: str, port: int) -> None:
        """处理保留的监听启动事件。

        Args:
            host: 监听主机文本。
            port: 监听端口。

        Returns:
            None: 默认不执行任何操作。
        """

    def on_listen_stopping(self) -> None:
        """处理交换实例即将停止的事件。

        Returns:
            None: 默认不执行任何操作。
        """

    def on_jacks_dial_plan(self, jacks: Sequence[tuple[str, str]]) -> None:
        """处理接入点计划加载完成的事件。

        Args:
            jacks: 接入点名称与地址列表。

        Returns:
            None: 默认不执行任何操作。
        """

    def on_jack_connected(self, jack_name: str, remote: str | None) -> None:
        """处理接入点已连接的事件。

        Args:
            jack_name: 已连接的接入点名称。
            remote: 对端地址文本；无法取得时为 None。

        Returns:
            None: 默认不执行任何操作。
        """

    def on_jack_disconnected(self, jack_name: str) -> None:
        """处理接入点已断开的事件。

        Args:
            jack_name: 已断开的接入点名称。

        Returns:
            None: 默认不执行任何操作。
        """

    def on_incoming_send(
        self, from_jack: str, payload: bytes, seq: int | None
    ) -> None:
        """处理接入点发来的入站数据。

        Args:
            from_jack: 来源接入点名称。
            payload: 原始业务载荷。
            seq: 入站序号；没有序号时为 None。

        Returns:
            None: 默认不执行任何操作。
        """

    def on_route_skipped(
        self,
        from_jack: str,
        to_jack: str,
        payload: bytes,
        *,
        reason: str,
        detail: str | None = None,
    ) -> None:
        """处理某条连线未投递的事件。

        Args:
            from_jack: 来源接入点名称。
            to_jack: 目标接入点名称。
            payload: 原始业务载荷。
            reason: 跳过原因，常见值为 `rule`、`offline` 或 `patch`。
            detail: 额外说明；没有说明时为 None。

        Returns:
            None: 默认不执行任何操作。
        """

    def on_packet_delivered(self, from_jack: str, to_jack: str, payload: bytes) -> None:
        """处理数据已成功投递的事件。

        Args:
            from_jack: 来源接入点名称。
            to_jack: 目标接入点名称。
            payload: 已投递的业务载荷。

        Returns:
            None: 默认不执行任何操作。
        """

    def on_deliver_failed(
        self,
        from_jack: str,
        to_jack: str,
        payload: bytes,
        error: BaseException | None,
    ) -> None:
        """处理投递失败事件。

        Args:
            from_jack: 来源接入点名称。
            to_jack: 目标接入点名称。
            payload: 投递失败的业务载荷。
            error: 捕获到的异常；没有异常对象时为 None。

        Returns:
            None: 默认不执行任何操作。
        """
