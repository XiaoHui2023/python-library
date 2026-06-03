import asyncio
from collections.abc import Awaitable, Callable

from onebot_protocol import MessagePayload

from qq_adapter.bot import DEFAULT_INTENTS, QQBot
from qq_adapter.listener import (
    Listener,
    emit_disconnect,
    emit_error,
    emit_message,
    emit_void,
)
from qq_adapter.models import QQMessage
from qq_adapter.protocol_adapter import onebot_to_qq, qq_to_onebot

MessageCallback = Callable[[MessagePayload], Awaitable[None]]


class Adapter:
    """QQ 开放平台对外门面：入站转统一消息载荷，出站从载荷发回平台。

    平台专有结构与连接细节留在包内；调用方只依赖统一载荷类型与监听器事件。
    """

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        bot_id: str,
        *,
        proxy: str | None = None,
        intents: int = DEFAULT_INTENTS,
        listeners: list[Listener] | None = None,
    ) -> None:
        """创建适配器并绑定内部机器人客户端。

        Args:
            app_id: QQ 开放平台应用 ID
            app_secret: QQ 开放平台应用密钥
            bot_id: 机器人对外标识，写入出站载荷
            proxy: 可选 HTTP 代理 URL
            intents: 网关事件订阅位掩码
            listeners: 构造期注册的多组事件监听器
        """
        self._callbacks: list[MessageCallback] = []
        self._listeners: list[Listener] = list(listeners or [])
        self._bot = QQBot(
            app_id=app_id,
            app_secret=app_secret,
            bot_id=bot_id,
            proxy=proxy,
            intents=intents,
        )
        self._bot.on_message(self._on_qq_message)
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
        """按统一载荷向当前会话发送回复。

        Args:
            payload: 目标会话与消息段列表
        """
        await self._bot.send_message(onebot_to_qq(payload))

    async def _on_qq_message(self, msg: QQMessage) -> None:
        payload = qq_to_onebot(msg)
        await emit_message(self._listeners, payload)
        for callback in self._callbacks:
            asyncio.create_task(self._invoke(callback, payload))

    async def _on_connect(self) -> None:
        await emit_void(self._listeners, "on_connect")

    async def _on_ready(self) -> None:
        await emit_void(self._listeners, "on_ready")

    async def _on_disconnect(self, reason: str) -> None:
        await emit_disconnect(self._listeners, reason)

    async def _on_error(self, exc: BaseException) -> None:
        await emit_error(self._listeners, exc)

    async def _invoke(
        self, callback: MessageCallback, payload: MessagePayload
    ) -> None:
        try:
            await callback(payload)
        except Exception:
            pass

    async def start(self) -> None:
        """在后台启动网关连接，不阻塞当前协程。

        与 stop 配对；长期运行请用 run。
        """
        await emit_void(self._listeners, "on_start")
        await self._bot.start()

    async def stop(self) -> None:
        """停止网关并释放连接资源；会触发监听器的 on_stop。"""
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
