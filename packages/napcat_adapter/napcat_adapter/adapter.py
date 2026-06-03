from collections.abc import Awaitable, Callable

from onebot_protocol import MessagePayload

from napcat_adapter.bot import Bot
from napcat_adapter.listener import (
    Listener,
    emit_disconnect,
    emit_error,
    emit_message,
    emit_void,
)
from napcat_adapter.models import BotMessage
from napcat_adapter.protocol_adapt import bot_to_onebot, onebot_to_bot

MessageCallback = Callable[[MessagePayload], Awaitable[None]]


class Adapter:
    """NapCat 对外门面：入站转统一消息载荷，出站从载荷经 CQ 段发回。

    群聊默认仅在 @ 机器人时上报；过滤规则在包内完成。
    """

    def __init__(
        self,
        ws_url: str,
        *,
        token: str | None = None,
        reconnect_interval_seconds: float = 5.0,
        listeners: list[Listener] | None = None,
    ) -> None:
        """创建适配器并绑定内部 NapCat 客户端。

        Args:
            ws_url: NapCat 正向 WebSocket 地址
            token: 可选访问令牌
            reconnect_interval_seconds: 断线后重连等待秒数
            listeners: 构造期注册的多组事件监听器
        """
        self._callbacks: list[MessageCallback] = []
        self._listeners: list[Listener] = list(listeners or [])
        self._bot = Bot(
            ws_url=ws_url,
            token=token,
            reconnect_interval_seconds=reconnect_interval_seconds,
        )
        self._bot.on_message(self._on_bot_message)
        self._bot.on_connect(self._on_connect)
        self._bot.on_ready(self._on_ready)
        self._bot.on_disconnect(self._on_disconnect)
        self._bot.on_error(self._on_error)

    def register(self, callback: MessageCallback) -> None:
        """登记一条消息回调，与监听器中的消息槽位一并触发。

        Args:
            callback: 异步处理入站统一消息载荷
        """
        self._callbacks.append(callback)

    def on_message(
        self, callback: MessageCallback | None = None
    ) -> MessageCallback | Callable[[MessageCallback], MessageCallback]:
        """登记消息回调；无参调用时返回装饰器。

        Args:
            callback: 直接传入的异步处理函数；省略时用于装饰器写法

        Returns:
            装饰器模式下返回原函数；直接传入时返回同一回调
        """
        if callback is not None:
            self.register(callback)
            return callback

        def decorator(fn: MessageCallback) -> MessageCallback:
            self.register(fn)
            return fn

        return decorator

    async def send(self, payload: MessagePayload) -> None:
        """按统一载荷向当前会话发送消息。

        Args:
            payload: 目标会话与消息段列表
        """
        await self._bot.send(onebot_to_bot(payload))

    async def _on_bot_message(self, msg: BotMessage) -> None:
        payload = bot_to_onebot(msg)
        if payload is None:
            return
        await emit_message(self._listeners, payload)
        for callback in self._callbacks:
            try:
                await callback(payload)
            except Exception:
                pass

    async def _on_connect(self) -> None:
        await emit_void(self._listeners, "on_connect")

    async def _on_ready(self) -> None:
        await emit_void(self._listeners, "on_ready")

    async def _on_disconnect(self, reason: str) -> None:
        await emit_disconnect(self._listeners, reason)

    async def _on_error(self, exc: BaseException) -> None:
        await emit_error(self._listeners, exc)

    async def start(self) -> None:
        """在后台启动 WebSocket 事件循环，不阻塞当前协程。

        与 stop 配对；长期运行请用 run。
        """
        await emit_void(self._listeners, "on_start")
        await self._bot.start()

    async def stop(self) -> None:
        """停止客户端并结束事件循环；会触发监听器的 on_stop。"""
        await self._bot.stop()
        await emit_void(self._listeners, "on_stop")

    async def run(self) -> None:
        """启动并阻塞直到停止；适合 asyncio.run(adapter.run())。

        Ctrl+C 或任务取消时会断开连接并触发 on_stop。
        """
        await emit_void(self._listeners, "on_start")
        try:
            await self._bot.run()
        finally:
            await emit_void(self._listeners, "on_stop")
