from __future__ import annotations

import asyncio
import inspect
import itertools
import logging
import os
from collections.abc import Awaitable, Callable, Sequence

import aiohttp
from aiohttp import ClientWebSocketResponse

from .listeners import JackListener, emit_jack_listeners
from .protocol import Frame, decode_frame, encode_frame
from .transport.websocket import websocket_url

logger = logging.getLogger(__name__)

# 与 PatchBay 同机挂线时使用回环地址（不可将 0.0.0.0 作为对端地址）。
JACK_LOCAL_CONNECT_HOST = "127.0.0.1"

# 与 PatchBay 配置里 ``jacks[].name``、hello 帧里的标识一致；单进程多实例（如测试）时传不同 ``wire_id``。
DEFAULT_WIRE_ID = "jack"
ENV_WIRE_ID = "PATCH_BAY_JACK_ID"

PacketHandler = Callable[[bytes], Awaitable[None] | None]


class Jack:
    """业务侧接入点：像港口一样只与 PatchBay 这条「总线」打交道，**不与其他 Jack 直连**；往来字节由 PatchBay 按配置转发。
    构造为 ``Jack(port, ...)``；与交换机里该端点的标识见 ``wire_id``（默认与 ``PATCH_BAY_JACK_ID`` / ``jack`` 对齐）。
    收发数据包并接收经路由投递的回调（无通道，由载荷自行解析）。

    ``port`` 为 PatchBay 的挂入端口；同机时目标主机固定为 ``127.0.0.1``（PatchBay 监听 ``0.0.0.0``）。
    实现上由本进程向该端口建立接入链路，以便 PatchBay 单进程集中维护拓扑与转发（不必用「客户端 / 服务端」来理解业务关系）。

    **断线重连**：``start()`` 后在后台循环尝试挂入；首次失败或运行中断线，按指数退避重试（约 0.5s 起，上限 30s），直至 ``aclose()``。
    PatchBay 不负责代 Jack 重连；各 Jack 自行维护到 PatchBay 的链路。

    启动后需保持事件循环运行；常见写法为 ``await jack.start()`` 之后 ``await asyncio.Event().wait()`` 占位，
    在 ``asyncio.run(...)`` 外层捕获 ``KeyboardInterrupt`` 并在 ``finally`` 里 ``await jack.aclose()``，或使用
    ``await jack.join()`` 与别处调用的 ``aclose()`` 配对。使用 ``@jack`` 或 ``jack(函数)`` 注册收包回调（同 ``register``）。
    收到数据时所有已注册回调并行执行（异步 ``await``、同步走线程池）。
    同步回调在线程池中运行，勿在其中直接操作 asyncio 对象，回主循环请用 ``call_soon_threadsafe``。
    可选 ``listeners``：``JackListener`` 子类列表，用于链路生命周期与投递、发送等可观测事件（同步回调）。

    ``wire_id`` 与配置里该端点的 ``name`` 一致；省略时先用环境变量 ``PATCH_BAY_JACK_ID``，再默认 ``jack``。
    同一进程挂多个 ``Jack``（如集成测试）时需分别传入不同 ``wire_id``。
    """

    def __init__(
        self,
        port: int,
        *,
        wire_id: str | None = None,
        ws_path: str = "/ws",
        session: aiohttp.ClientSession | None = None,
        listeners: Sequence[JackListener] | None = None,
    ) -> None:
        if not (1 <= port <= 65535):
            raise ValueError(f"port must be 1..65535, got {port}")
        self._wire_id = (
            wire_id
            if wire_id is not None
            else os.environ.get(ENV_WIRE_ID, DEFAULT_WIRE_ID)
        )
        self._server = websocket_url(f"ws://{JACK_LOCAL_CONNECT_HOST}:{port}", ws_path)
        self._owns_session = session is None
        self._session = session or aiohttp.ClientSession()
        self._ws: ClientWebSocketResponse | None = None
        self._ws_lock = asyncio.Lock()
        self._seq = itertools.count(1)
        self._run_task: asyncio.Task[None] | None = None
        self._closed = asyncio.Event()
        self._stopped = asyncio.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._handlers: list[PacketHandler] = []
        self._listeners: list[JackListener] = list(listeners or ())

    def register(self, fn: PacketHandler) -> PacketHandler:
        """显式注册收包回调；与 ``jack(fn)`` / ``@jack`` 等价。"""
        self._handlers.append(fn)
        return fn

    def __call__(self, fn: PacketHandler) -> PacketHandler:
        """``@jack`` 或 ``jack(handler)`` 注册回调，等价于 ``register``。"""
        return self.register(fn)

    async def start(self) -> None:
        """启动后台挂入与重试循环；不阻塞等待首次挂入成功。"""
        if self._run_task is not None:
            return
        self._closed.clear()
        self._stopped.clear()
        self._loop = asyncio.get_running_loop()
        self._run_task = asyncio.create_task(self._connection_loop(), name=f"jack:{self._wire_id}")

    async def join(self) -> None:
        """阻塞直至 `aclose()` 完成，便于应用入口在 `start()` 后保持进程存活（配合 Ctrl+C 在协程外取消或捕获 KeyboardInterrupt）。"""
        await self._stopped.wait()

    async def aclose(self) -> None:
        """停止重试循环并关闭与 PatchBay 的链路。"""
        emit_jack_listeners(self._listeners, "on_stopping")
        self._closed.set()
        if self._run_task is not None:
            self._run_task.cancel()
            try:
                await self._run_task
            except asyncio.CancelledError:
                pass
            self._run_task = None
        async with self._ws_lock:
            if self._ws is not None and not self._ws.closed:
                await self._ws.close()
            self._ws = None
        if self._owns_session and not self._session.closed:
            await self._session.close()
        self._stopped.set()

    async def send(self, data: bytes) -> None:
        """向 PatchBay 发送一帧数据包（由路由广播/转发到对端）。"""
        async with self._ws_lock:
            ws = self._ws
            if ws is None or ws.closed:
                logger.warning("Jack %r: send dropped (not connected)", self._wire_id)
                emit_jack_listeners(self._listeners, "on_send_dropped", "not_connected")
                return
            seq = next(self._seq)
            frame = Frame(kind="send", payload=data, seq=seq)
            try:
                await ws.send_bytes(encode_frame(frame))
            except Exception:
                logger.warning("Jack %r: send failed, packet dropped", self._wire_id, exc_info=True)
                emit_jack_listeners(self._listeners, "on_send_failed")

    def send_sync(self, data: bytes) -> None:
        """同步发送；需在已有事件循环的上下文中使用。"""
        loop = self._loop
        if loop is None:
            raise RuntimeError("call start() before send_sync()")
        fut = asyncio.run_coroutine_threadsafe(self.send(data), loop)
        fut.result(timeout=30.0)

    async def _connection_loop(self) -> None:
        backoff = 0.5
        max_backoff = 30.0
        while not self._closed.is_set():
            try:
                async with self._session.ws_connect(self._server, autoping=True) as ws:
                    await self._handshake(ws)
                    async with self._ws_lock:
                        self._ws = ws
                    emit_jack_listeners(self._listeners, "on_link_up")
                    backoff = 0.5
                    try:
                        await self._recv_loop(ws)
                    finally:
                        emit_jack_listeners(self._listeners, "on_link_down")
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Jack %r connection error, reconnecting", self._wire_id)
            finally:
                async with self._ws_lock:
                    self._ws = None
            if self._closed.is_set():
                break
            delay = min(backoff, max_backoff)
            logger.warning(
                "Jack %r disconnected or failed; retry in %.1fs",
                self._wire_id,
                delay,
            )
            try:
                await asyncio.wait_for(self._closed.wait(), timeout=delay)
                break
            except asyncio.TimeoutError:
                pass
            backoff = min(backoff * 2, max_backoff)

    async def _handshake(self, ws: ClientWebSocketResponse) -> None:
        hello = Frame(kind="hello", jack=self._wire_id)
        await ws.send_bytes(encode_frame(hello))

    async def _recv_loop(self, ws: ClientWebSocketResponse) -> None:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.BINARY:
                try:
                    frame = decode_frame(msg.data)
                except Exception:
                    logger.exception("Jack %r invalid frame", self._wire_id)
                    continue
                await self._dispatch_frame(frame)
            elif msg.type == aiohttp.WSMsgType.ERROR:
                break

    async def _dispatch_frame(self, frame: Frame) -> None:
        if frame.kind == "deliver" and frame.payload is not None:
            emit_jack_listeners(self._listeners, "on_incoming_deliver", frame.payload)
            await self._emit_payload_parallel(frame.payload)
        elif frame.kind == "error" and frame.payload is not None:
            msg = frame.payload.decode("utf-8", errors="replace")
            logger.error("PatchBay error for %s: %s", self._wire_id, msg)
            emit_jack_listeners(self._listeners, "on_patchbay_error", msg)
        elif frame.kind == "ack" and frame.seq is not None:
            emit_jack_listeners(self._listeners, "on_ack", frame.seq)
            logger.debug("Jack %s ack seq=%s", self._wire_id, frame.seq)

    async def _emit_payload_parallel(self, payload: bytes) -> None:
        if not self._handlers:
            return
        loop = asyncio.get_running_loop()

        async def _one(h: PacketHandler) -> None:
            if inspect.iscoroutinefunction(h):
                await h(payload)
            else:
                await loop.run_in_executor(None, h, payload)

        results = await asyncio.gather(*(_one(h) for h in self._handlers), return_exceptions=True)
        for i, res in enumerate(results):
            if isinstance(res, BaseException):
                logger.error(
                    "Jack %r handler[%s] failed",
                    self._wire_id,
                    i,
                    exc_info=(type(res), res, res.__traceback__),
                )
