from __future__ import annotations

import asyncio
import inspect
import itertools
import logging
from collections.abc import Awaitable, Callable

import aiohttp
from aiohttp import ClientWebSocketResponse

from .protocol import Frame, decode_frame, encode_frame
from .transport.websocket import websocket_url

logger = logging.getLogger(__name__)

PacketHandler = Callable[[bytes], Awaitable[None] | None]


class Jack:
    """业务端点：连接 PatchBay，发送数据包并接收触发回调（无通道，由载荷自行解析）。

    **断线重连**：``start()`` 后在后台循环连接；首次连不上、或运行中断线，都会按指数退避等待后自动重试（约 0.5s 起，上限 30s），直至 ``aclose()``。
    PatchBay 作为服务端只负责接受连接，本身不做「重连」；各 Jack 进程自行维护到 PatchBay 的长连接。

    启动后需保持事件循环运行；常见写法为 ``await jack.start()`` 之后 ``await asyncio.Event().wait()`` 占位，
    在 ``asyncio.run(...)`` 外层捕获 ``KeyboardInterrupt`` 并在 ``finally`` 里 ``await jack.aclose()``，或使用
    ``await jack.join()`` 与别处调用的 ``aclose()`` 配对。使用 ``@jack`` 或 ``jack(函数)`` 注册收包回调（同 ``register``）。
    收到数据时所有已注册回调并行执行（异步 ``await``、同步走线程池）。
    同步回调在线程池中运行，勿在其中直接操作 asyncio 对象，回主循环请用 ``call_soon_threadsafe``。
    """

    def __init__(
        self,
        name: str,
        server: str,
        *,
        ws_path: str = "/ws",
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self.name = name
        self._server = websocket_url(server, ws_path)
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

    def register(self, fn: PacketHandler) -> PacketHandler:
        """显式注册收包回调；与 ``jack(fn)`` / ``@jack`` 等价。"""
        self._handlers.append(fn)
        return fn

    def __call__(self, fn: PacketHandler) -> PacketHandler:
        """``@jack`` 或 ``jack(handler)`` 注册回调，等价于 ``register``。"""
        return self.register(fn)

    async def start(self) -> None:
        """启动后台连接与重连循环；不阻塞等待首次连接成功。"""
        if self._run_task is not None:
            return
        self._closed.clear()
        self._stopped.clear()
        self._loop = asyncio.get_running_loop()
        self._run_task = asyncio.create_task(self._connection_loop(), name=f"jack:{self.name}")

    async def join(self) -> None:
        """阻塞直至 `aclose()` 完成，便于应用入口在 `start()` 后保持进程存活（配合 Ctrl+C 在协程外取消或捕获 KeyboardInterrupt）。"""
        await self._stopped.wait()

    async def aclose(self) -> None:
        """停止重连循环并关闭连接。"""
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
                logger.warning("Jack %r: send dropped (not connected)", self.name)
                return
            seq = next(self._seq)
            frame = Frame(kind="send", payload=data, seq=seq)
            try:
                await ws.send_bytes(encode_frame(frame))
            except Exception:
                logger.warning("Jack %r: send failed, packet dropped", self.name, exc_info=True)

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
                    backoff = 0.5
                    await self._recv_loop(ws)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Jack %r connection error, reconnecting", self.name)
            finally:
                async with self._ws_lock:
                    self._ws = None
            if self._closed.is_set():
                break
            delay = min(backoff, max_backoff)
            logger.warning(
                "Jack %r disconnected or failed; retry in %.1fs",
                self.name,
                delay,
            )
            try:
                await asyncio.wait_for(self._closed.wait(), timeout=delay)
                break
            except asyncio.TimeoutError:
                pass
            backoff = min(backoff * 2, max_backoff)

    async def _handshake(self, ws: ClientWebSocketResponse) -> None:
        hello = Frame(kind="hello", jack=self.name)
        await ws.send_bytes(encode_frame(hello))

    async def _recv_loop(self, ws: ClientWebSocketResponse) -> None:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.BINARY:
                try:
                    frame = decode_frame(msg.data)
                except Exception:
                    logger.exception("Jack %r invalid frame", self.name)
                    continue
                await self._dispatch_frame(frame)
            elif msg.type == aiohttp.WSMsgType.ERROR:
                break

    async def _dispatch_frame(self, frame: Frame) -> None:
        if frame.kind == "deliver" and frame.payload is not None:
            await self._emit_payload_parallel(frame.payload)
        elif frame.kind == "error" and frame.payload is not None:
            logger.error(
                "PatchBay error for %s: %s",
                self.name,
                frame.payload.decode("utf-8", errors="replace"),
            )
        elif frame.kind == "ack" and frame.seq is not None:
            logger.debug("Jack %s ack seq=%s", self.name, frame.seq)

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
                    self.name,
                    i,
                    exc_info=(type(res), res, res.__traceback__),
                )
