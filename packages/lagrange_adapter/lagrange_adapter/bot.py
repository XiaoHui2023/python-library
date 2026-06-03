from aiocqhttp import CQHttp, Event
from collections.abc import Awaitable, Callable
from contextlib import suppress

import asyncio
from pydantic import BaseModel, Field

from lagrange_adapter.models import BotMessage, MessageType

VoidCallback = Callable[[], Awaitable[None]]
DisconnectCallback = Callable[[str], Awaitable[None]]
ErrorCallback = Callable[[BaseException], Awaitable[None]]


class Bot(BaseModel):
    """Lagrange 反向 WebSocket 服务：接收 CQ 事件并回发消息。

    构造入参见各字段的 description；包外请优先使用 Adapter。
    """

    port: int = Field(default=6199, description="本机监听端口，供 Lagrange 连接")

    def model_post_init(self, ctx: object) -> None:
        """初始化运行期状态与事件槽位。"""
        self._stop_event = asyncio.Event()

        self._bot = None
        self._login_info = None
        self._bot_name: str = None
        self._bot_id: str = None
        self._running = False
        self._on_message: Callable[[BotMessage], Awaitable[None]] | None = None
        self._on_connect: VoidCallback | None = None
        self._on_ready: VoidCallback | None = None
        self._on_disconnect: DisconnectCallback | None = None
        self._on_error: ErrorCallback | None = None
        self._ws_task: asyncio.Task[None] | None = None

    def on_message(self, callback: Callable[[BotMessage], Awaitable[None]]) -> None:
        """登记入站聊天事件回调。

        Args:
            callback: 异步处理包内机器人消息
        """
        self._on_message = callback

    def on_connect(self, callback: VoidCallback) -> None:
        """登记 WebSocket 已连接回调。"""
        self._on_connect = callback

    def on_ready(self, callback: VoidCallback) -> None:
        """登记登录信息就绪回调。"""
        self._on_ready = callback

    def on_disconnect(self, callback: DisconnectCallback) -> None:
        """登记连接断开回调。

        Args:
            callback: 异步处理断开原因短句
        """
        self._on_disconnect = callback

    def on_error(self, callback: ErrorCallback) -> None:
        """登记运行期错误回调。

        Args:
            callback: 异步处理异常对象
        """
        self._on_error = callback

    async def _emit_connect(self) -> None:
        if self._on_connect is None:
            return
        try:
            await self._on_connect()
        except Exception:
            pass

    async def _emit_ready(self) -> None:
        if self._on_ready is None:
            return
        try:
            await self._on_ready()
        except Exception:
            pass

    async def _emit_disconnect(self, reason: str) -> None:
        if self._on_disconnect is None:
            return
        try:
            await self._on_disconnect(reason)
        except Exception:
            pass

    async def _emit_error(self, exc: BaseException) -> None:
        if self._on_error is None:
            return
        try:
            await self._on_error(exc)
        except Exception:
            pass

    async def _get_login_info(self):
        try:
            self._login_info = await self._bot.get_login_info()
            self._bot_name = self._login_info["nickname"]
            self._bot_id = str(self._login_info["user_id"])
        except Exception:
            pass

    async def _handle_ws(self):
        self._bot = CQHttp(api_root='')

        @self._bot.on_websocket_connection
        async def _(_):
            await self._emit_connect()
            await self._get_login_info()
            await self._emit_ready()

        @self._bot.on_message
        async def _(event: Event, **kwargs):
            if self._login_info is None:
                await self._get_login_info()

            user_name = str(event.user_id)
            session_id = str(event.group_id) if event.message_type == 'group' else user_name
            message_type = MessageType.GROUP if event.message_type == 'group' else MessageType.PRIVATE
            data_list = event.message
            message_id = str(event.message_id)

            message = BotMessage(
                session_id=session_id,
                data_list=data_list,
                bot_id=self._bot_id,
                message_type=message_type,
                user_name=user_name,
                message_id=message_id,
                bot_name=self._bot_name,
            )

            if self._on_message is not None:
                try:
                    await self._on_message(message)
                except Exception:
                    pass

        @self._bot.on('error')
        async def _(event: Event):
            await self._emit_error(RuntimeError(str(event)))

        try:
            await self._bot.run_task(
                host='0.0.0.0',
                port=self.port,
                shutdown_trigger=self._stop_event.wait,
            )
        finally:
            await self._emit_disconnect("stopped")

    async def start(self) -> None:
        """在后台启动反向 WebSocket 服务，不阻塞当前协程。"""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._ws_task = asyncio.create_task(self._handle_ws())

    async def send(self, message: BotMessage) -> None:
        """向群或好友发送 CQ 段列表。

        Args:
            message: 含会话类型与 data_list 的包内消息
        """
        data_list = [
            {"type": segment["type"], "data": segment.get("data", {})}
            for segment in message.data_list
        ]

        try:
            sid = int(message.session_id)
            if message.message_type == MessageType.GROUP:
                await self._bot.send_msg(
                    message_type="group",
                    group_id=sid,
                    message=data_list,
                )
            else:
                await self._bot.send_msg(
                    message_type="private",
                    user_id=sid,
                    message=data_list,
                )
        except Exception:
            pass

    async def stop(self) -> None:
        """触发关闭并结束常驻运行。"""
        if not self._running:
            self._stop_event.set()
            return
        self._running = False
        self._stop_event.set()
        if self._ws_task is not None and self._ws_task is not asyncio.current_task():
            self._ws_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._ws_task
        self._ws_task = None

    async def run(self) -> None:
        """启动服务并阻塞；Ctrl+C 或任务取消时收尾退出。"""
        await self.start()
        try:
            await self._stop_event.wait()
        finally:
            await self.stop()
