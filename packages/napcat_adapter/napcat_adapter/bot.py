import asyncio
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import Any

from napcat import GroupMessageEvent, NapCatClient, PrivateMessageEvent
from napcat.types.messages import Message, MessageSegment, UnknownMessageSegment
from pydantic import BaseModel, Field, PrivateAttr

from napcat_adapter.models import BotMessage, MessageType

VoidCallback = Callable[[], Awaitable[None]]
DisconnectCallback = Callable[[str], Awaitable[None]]
ErrorCallback = Callable[[BaseException], Awaitable[None]]
SEND_ATTEMPTS = 3
SEND_RETRY_DELAYS = (1.0, 3.0)
SEND_RETRY_EXCEPTIONS = (
    TimeoutError,
    asyncio.TimeoutError,
    ConnectionError,
    OSError,
)
FILE_LIKE_SEGMENT_TYPES = frozenset({"image", "record", "file", "video"})


class Bot(BaseModel):
    """NapCat 正向 WebSocket 客户端：收事件、发 CQ 消息。

    构造入参见各字段的 description；包外请优先使用 Adapter。
    """

    ws_url: str = Field(description="NapCat 正向 WebSocket 地址")
    token: str | None = Field(default=None, description="NapCat 访问令牌")
    reconnect_interval_seconds: float = Field(
        default=5.0,
        ge=0.5,
        le=3600.0,
        description="断线或连接失败后再次尝试前的等待秒数",
    )

    _stop_event: asyncio.Event = PrivateAttr()
    _task: asyncio.Task[None] | None = PrivateAttr(default=None)
    _client: NapCatClient | None = PrivateAttr(default=None)
    _login_info: dict[str, Any] | None = PrivateAttr(default=None)
    _bot_name: str = PrivateAttr(default="")
    _bot_id: str = PrivateAttr(default="")
    _running: bool = PrivateAttr(default=False)
    _on_message: Callable[[BotMessage], Awaitable[None]] | None = PrivateAttr(default=None)
    _on_connect: VoidCallback | None = PrivateAttr(default=None)
    _on_ready: VoidCallback | None = PrivateAttr(default=None)
    _on_disconnect: DisconnectCallback | None = PrivateAttr(default=None)
    _on_error: ErrorCallback | None = PrivateAttr(default=None)

    def model_post_init(self, ctx: Any) -> None:
        """初始化运行期状态与事件槽位。"""
        self._stop_event = asyncio.Event()

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

    async def _refresh_login_info(self) -> None:
        if self._client is None:
            return
        try:
            login_info = await self._client.get_login_info()
            user_id = int(login_info["user_id"])
            self._client.self_id = user_id
            self._login_info = dict(login_info)
            self._bot_id = str(user_id)
            self._bot_name = str(login_info["nickname"])
        except Exception:
            pass

    async def _handle_events(self) -> None:
        try:
            while not self._stop_event.is_set():
                self._client = NapCatClient(ws_url=self.ws_url, token=self.token)

                try:
                    async with self._client:
                        await self._emit_connect()
                        await self._refresh_login_info()
                        await self._emit_ready()
                        async for event in self._client:
                            if self._stop_event.is_set():
                                break
                            if isinstance(event, (GroupMessageEvent, PrivateMessageEvent)):
                                await self._handle_message(event)
                except asyncio.CancelledError:
                    raise
                except ConnectionRefusedError as exc:
                    await self._emit_error(exc)
                    await self._emit_disconnect("connection_refused")
                except Exception as exc:
                    await self._emit_error(exc)
                    await self._emit_disconnect("error")
                else:
                    if self._stop_event.is_set():
                        await self._emit_disconnect("stopped")
                    else:
                        await self._emit_disconnect("closed")
                finally:
                    self._client = None
                    self._login_info = None
                    self._bot_id = ""
                    self._bot_name = ""

                if self._stop_event.is_set():
                    break

                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=self.reconnect_interval_seconds,
                    )
                    break
                except TimeoutError:
                    continue
        finally:
            self._running = False

    async def _handle_message(self, event: GroupMessageEvent | PrivateMessageEvent) -> None:
        if self._login_info is None:
            await self._refresh_login_info()

        user_name = str(event.user_id)
        session_id = str(event.group_id) if isinstance(event, GroupMessageEvent) else user_name
        message_type = MessageType.GROUP if isinstance(event, GroupMessageEvent) else MessageType.PRIVATE
        data_list = [dict(segment) for segment in event.message]

        message = BotMessage(
            session_id=session_id,
            data_list=data_list,
            bot_id=self._bot_id,
            message_type=message_type,
            user_name=user_name,
            message_id=str(event.message_id),
            bot_name=self._bot_name,
        )

        if self._on_message is None:
            return
        try:
            await self._on_message(message)
        except Exception:
            pass

    async def start(self) -> None:
        """在后台启动 WebSocket 事件循环，不阻塞当前协程。"""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._task = asyncio.create_task(self._handle_events())

    async def send(self, message: BotMessage) -> None:
        """向群或好友发送 CQ 段列表。

        Args:
            message: 含会话类型与 data_list 的包内消息
        """
        if self._client is None or not self._client.is_running:
            raise RuntimeError("NapCat client is not connected")

        data_list = [
            {"type": segment["type"], "data": segment.get("data", {})}
            for segment in message.data_list
        ]
        sent_any = False
        first_error: BaseException | None = None
        for batch in _split_send_batches(data_list):
            messages = _to_napcat_messages(batch)
            if not messages:
                continue
            try:
                await self._send_with_retry(message, messages)
                sent_any = True
            except Exception as exc:
                if first_error is None:
                    first_error = exc
                if not _has_file_like_segment(batch):
                    raise

        if not sent_any:
            if first_error is not None:
                raise RuntimeError("NapCat message has no sendable segments sent") from first_error
            raise RuntimeError("NapCat message has no sendable segments")

    async def _send_with_retry(self, message: BotMessage, messages: list[Message]) -> None:
        last_error: BaseException | None = None
        for attempt in range(SEND_ATTEMPTS):
            try:
                if message.message_type == MessageType.GROUP:
                    await self._client.send_group_msg(
                        group_id=message.session_id, message=messages
                    )
                else:
                    await self._client.send_private_msg(
                        user_id=message.session_id, message=messages
                    )
                return
            except SEND_RETRY_EXCEPTIONS as exc:
                if attempt >= SEND_ATTEMPTS - 1:
                    raise RuntimeError(
                        f"NapCat send failed after {SEND_ATTEMPTS} attempts"
                    ) from exc
                last_error = exc
                await asyncio.sleep(SEND_RETRY_DELAYS[attempt])
        raise RuntimeError(f"NapCat send failed: {last_error}")

    async def stop(self) -> None:
        """停止客户端并结束事件循环。"""
        if not self._running:
            return
        self._stop_event.set()
        if self._task is not None and self._task is not asyncio.current_task():
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
        self._running = False

    async def run(self) -> None:
        """启动连接并阻塞；Ctrl+C 或任务取消时收尾退出。"""
        await self.start()
        try:
            await self._stop_event.wait()
        finally:
            await self.stop()


def _to_napcat_messages(data_list: list[dict[str, Any]]) -> list[Message]:
    """把 CQ 字典段列表转为 NapCat SDK 消息对象，跳过未知段。"""
    messages: list[Message] = []
    for data in data_list:
        segment = MessageSegment.from_dict(data)
        if isinstance(segment, UnknownMessageSegment):
            continue
        messages.append(segment)
    return messages


def _split_send_batches(data_list: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    batches: list[list[dict[str, Any]]] = []
    pending: list[dict[str, Any]] = []
    for data in data_list:
        if _has_file_like_segment([data]):
            if pending:
                batches.append(pending)
                pending = []
            batches.append([data])
        else:
            pending.append(data)
    if pending:
        batches.append(pending)
    return batches


def _has_file_like_segment(data_list: list[dict[str, Any]]) -> bool:
    for data in data_list:
        if data.get("type") in FILE_LIKE_SEGMENT_TYPES:
            return True
    return False
