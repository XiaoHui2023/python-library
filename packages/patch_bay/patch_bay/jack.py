from __future__ import annotations

import asyncio
import dataclasses
import inspect
import itertools
import logging
import os
import types
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Annotated, Any, Union, get_args, get_origin, get_type_hints

import aiohttp
from aiohttp import ClientWebSocketResponse
from pydantic import BaseModel, ValidationError

from ._interrupt import wait_until_interrupt
from .codec.packet import decode_application_packet, encode_application_packet
from .listeners import JackListener, emit_jack_listeners
from .protocol import Frame, decode_frame, encode_frame
from .transport.websocket import websocket_url

logger = logging.getLogger(__name__)

# 与 PatchBay 同机挂线时使用回环地址（不可将 0.0.0.0 作为对端地址）。
JACK_LOCAL_CONNECT_HOST = "127.0.0.1"

# 本端在 PatchBay ``jacks`` 里为该 Jack 配置的 ``address``；也可只设环境变量。
ENV_ADDRESS = "PATCH_BAY_ADDRESS"

PacketHandler = Callable[..., Awaitable[None] | None]


def _unwrap_annotated(ann: Any) -> Any:
    o = get_origin(ann)
    if o is Annotated:
        return get_args(ann)[0]
    return ann


def _is_union_origin(o: Any) -> bool:
    if o is Union:
        return True
    ut = getattr(types, "UnionType", None)
    return ut is not None and o is ut


def _match_one(ann: Any, decoded: Any) -> tuple[bool, Any]:
    """按单个注解校验/转换 ``decoded``；返回 ``(False, _)`` 表示应跳过回调。"""
    ann = _unwrap_annotated(ann)
    o = get_origin(ann)
    if _is_union_origin(o):
        for a in get_args(ann):
            if a is type(None):
                if decoded is None:
                    return True, None
                continue
            ok, val = _match_one(a, decoded)
            if ok:
                return True, val
        logger.error(
            "Jack 收包与回调形参类型不符：无法匹配 Union，实际类型为 %s",
            type(decoded).__name__,
        )
        return False, None
    if ann is Any:
        return True, decoded
    if isinstance(ann, type) and issubclass(ann, BaseModel):
        try:
            return True, ann.model_validate(decoded)
        except ValidationError as e:
            logger.error("Jack 收包与回调形参类型不符（model_validate）：%s", e)
            return False, None
    if ann is dict or get_origin(ann) is dict:
        if isinstance(decoded, dict):
            return True, decoded
        logger.error(
            "Jack 收包与回调形参类型不符：需要 dict，实际为 %s",
            type(decoded).__name__,
        )
        return False, None
    if ann is list or get_origin(ann) is list:
        if isinstance(decoded, list):
            return True, decoded
        logger.error(
            "Jack 收包与回调形参类型不符：需要 list，实际为 %s",
            type(decoded).__name__,
        )
        return False, None
    mo = get_origin(ann)
    if mo is not None and isinstance(mo, type) and mo is not dict and issubclass(mo, Mapping):
        if isinstance(decoded, dict):
            return True, decoded
        logger.error(
            "Jack 收包与回调形参类型不符：需要 mapping，实际为 %s",
            type(decoded).__name__,
        )
        return False, None
    if isinstance(ann, type) and dataclasses.is_dataclass(ann):
        if isinstance(decoded, ann):
            return True, decoded
        if isinstance(decoded, dict):
            try:
                return True, ann(**decoded)
            except TypeError as e:
                logger.error("Jack 收包与回调形参类型不符（dataclass）：%s", e)
                return False, None
        logger.error(
            "Jack 收包与回调形参类型不符：需要 %s 或对应 dict，实际为 %s",
            ann.__name__,
            type(decoded).__name__,
        )
        return False, None
    if isinstance(ann, type):
        if isinstance(decoded, ann):
            return True, decoded
        logger.error(
            "Jack 收包与回调形参类型不符：需要 %s，实际为 %s",
            ann.__name__,
            type(decoded).__name__,
        )
        return False, None
    return True, decoded


def _prepare_handler_arg(fn: Callable[..., Any], decoded: Any) -> tuple[bool, Any]:
    try:
        hints = get_type_hints(fn)
    except Exception:
        hints = {}
    sig = inspect.signature(fn)
    params = list(sig.parameters.values())
    if not params:
        return True, decoded
    first = params[0].name
    ann = hints.get(first)
    if ann is None:
        return True, decoded
    return _match_one(ann, decoded)


class Jack:
    """业务侧接入点：只与 PatchBay 这条「总线」打交道，**不与其他 Jack 直连**；往来数据包由 PatchBay 按配置转发。

    构造为 ``Jack(port, address=...)``：只需本机 **地址**（与 PatchBay 配置里对应条目的 ``address`` 一致），**没有 name/id**；
    交换机侧仍用 ``name`` + ``address`` 声明、用 ``name`` 连线，便于配置复用。

    ``port`` 为 PatchBay 的挂入端口；同机时目标主机固定为 ``127.0.0.1``。

    **断线重连**：``start()`` 后在后台循环尝试挂入；首次失败或运行中断线，按指数退避重试（约 0.5s 起，上限 30s），直至 ``aclose()``。

    可选 ``listeners``：``JackListener`` 子类列表（同步回调）。
    """

    def __init__(
        self,
        port: int,
        *,
        address: str | None = None,
        ws_path: str = "/ws",
        session: aiohttp.ClientSession | None = None,
        listeners: Sequence[JackListener] | None = None,
    ) -> None:
        if not (1 <= port <= 65535):
            raise ValueError(f"port must be 1..65535, got {port}")
        raw = (address if address is not None else os.environ.get(ENV_ADDRESS)) or ""
        self._address = str(raw).strip()
        if not self._address:
            raise ValueError(
                f"需要本端 address=…，或设置环境变量 {ENV_ADDRESS}（须与 PatchBay 配置中该 Jack 的 address 一致）"
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
        self._aclose_done = False

    def register(self, fn: PacketHandler) -> PacketHandler:
        """显式注册收包回调；与 ``jack(fn)`` / ``@jack`` 等价。

        投递到回调的是已解码的数据包（msgpack 反序列化结果，多为 ``dict``）；若为首形参标注了类型，
        则投递前校验；不匹配时 ``logging.error`` 并跳过该回调，不中断 Jack 运行。
        """
        self._handlers.append(fn)
        return fn

    def __call__(self, fn: PacketHandler) -> PacketHandler:
        """``@jack`` 或 ``jack(handler)`` 注册回调，等价于 ``register``。"""
        return self.register(fn)

    async def start(self) -> None:
        """启动后台挂入与重试循环；不阻塞等待首次挂入成功。"""
        if self._run_task is not None:
            return
        self._aclose_done = False
        self._closed.clear()
        self._stopped.clear()
        self._loop = asyncio.get_running_loop()
        self._run_task = asyncio.create_task(self._connection_loop(), name=f"jack:{self._address}")

    async def join(self) -> None:
        """阻塞直至 `aclose()` 完成，便于应用入口在 `start()` 后保持进程存活（配合 Ctrl+C 在协程外取消或捕获 KeyboardInterrupt）。"""
        await self._stopped.wait()

    async def run(self) -> None:
        """等价于 ``start()`` + 阻塞直至退出信号或主任务取消 + ``aclose()``。

        适合 ``asyncio.run(jack.run())`` 占满主线程；Ctrl+C 会先结束阻塞再清理连接。
        """
        await self.start()
        try:
            await wait_until_interrupt()
        except asyncio.CancelledError:
            raise
        finally:
            await self.aclose()

    async def aclose(self) -> None:
        """停止重试循环并关闭与 PatchBay 的链路。"""
        if self._aclose_done:
            return
        self._aclose_done = True
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

    async def send(self, packet: object) -> None:
        """向 PatchBay 发送一帧业务数据包（dict/Mapping、Pydantic 模型或 dataclass 实例），由路由转发到对端。

        负载经 msgpack 编码后置于协议帧 ``payload`` 中。
        """
        try:
            data = encode_application_packet(packet)
        except TypeError:
            raise
        except Exception:
            logger.exception("Jack %r: 无法编码数据包", self._address)
            return
        async with self._ws_lock:
            ws = self._ws
            if ws is None or ws.closed:
                logger.warning("Jack %r: send dropped (not connected)", self._address)
                emit_jack_listeners(self._listeners, "on_send_dropped", "not_connected")
                return
            seq = next(self._seq)
            frame = Frame(kind="send", payload=data, seq=seq)
            try:
                await ws.send_bytes(encode_frame(frame))
            except Exception:
                logger.warning("Jack %r: send failed, packet dropped", self._address, exc_info=True)
                emit_jack_listeners(self._listeners, "on_send_failed")

    def send_sync(self, packet: object) -> None:
        """同步发送；需在已有事件循环的上下文中使用。"""
        loop = self._loop
        if loop is None:
            raise RuntimeError("call start() before send_sync()")
        fut = asyncio.run_coroutine_threadsafe(self.send(packet), loop)
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
                logger.exception("Jack %r connection error, reconnecting", self._address)
            finally:
                async with self._ws_lock:
                    self._ws = None
            if self._closed.is_set():
                break
            delay = min(backoff, max_backoff)
            logger.warning(
                "Jack %r disconnected or failed; retry in %.1fs",
                self._address,
                delay,
            )
            try:
                await asyncio.wait_for(self._closed.wait(), timeout=delay)
                break
            except asyncio.TimeoutError:
                pass
            backoff = min(backoff * 2, max_backoff)

    async def _handshake(self, ws: ClientWebSocketResponse) -> None:
        hello = Frame(kind="hello", address=self._address)
        await ws.send_bytes(encode_frame(hello))

    async def _recv_loop(self, ws: ClientWebSocketResponse) -> None:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.BINARY:
                try:
                    frame = decode_frame(msg.data)
                except Exception:
                    logger.exception("Jack %r invalid frame", self._address)
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
            logger.error("PatchBay error for %s: %s", self._address, msg)
            emit_jack_listeners(self._listeners, "on_patchbay_error", msg)
        elif frame.kind == "ack" and frame.seq is not None:
            emit_jack_listeners(self._listeners, "on_ack", frame.seq)
            logger.debug("Jack %s ack seq=%s", self._address, frame.seq)

    async def _emit_payload_parallel(self, payload: bytes) -> None:
        if not self._handlers:
            return
        try:
            decoded = decode_application_packet(payload)
        except Exception:
            logger.error("Jack %r 无法解码数据包（非合法 msgpack 负载）", self._address, exc_info=True)
            return
        loop = asyncio.get_running_loop()

        async def _one(h: PacketHandler) -> None:
            ok, arg = _prepare_handler_arg(h, decoded)
            if not ok:
                return
            if inspect.iscoroutinefunction(h):
                await h(arg)
            else:
                await loop.run_in_executor(None, h, arg)

        results = await asyncio.gather(*(_one(h) for h in self._handlers), return_exceptions=True)
        for i, res in enumerate(results):
            if isinstance(res, BaseException):
                logger.error(
                    "Jack %r handler[%s] failed",
                    self._address,
                    i,
                    exc_info=(type(res), res, res.__traceback__),
                )
