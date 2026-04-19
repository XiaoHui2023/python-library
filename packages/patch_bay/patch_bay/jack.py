from __future__ import annotations

import asyncio
import dataclasses
import inspect
import itertools
import logging
import types
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Annotated, Any, Union, get_args, get_origin, get_type_hints

import aiohttp
from aiohttp import web
from pydantic import BaseModel, ValidationError

from ._interrupt import wait_until_interrupt
from .codec.packet import decode_application_packet, encode_application_packet
from .listeners import JackListener, emit_jack_listeners
from .protocol import Frame, decode_frame, encode_frame

logger = logging.getLogger(__name__)

PacketHandler = Callable[..., Awaitable[None] | None]


def _effective_listen_host_port(site: web.BaseSite, host: str, port: int) -> tuple[str, int]:
    if port != 0:
        return host, port
    srv = getattr(site, "_server", None)
    if srv is None:
        return host, port
    socks = getattr(srv, "sockets", None)
    if not socks:
        return host, port
    addr = socks[0].getsockname()
    if isinstance(addr, tuple) and len(addr) >= 2:
        return str(addr[0]), int(addr[1])
    return host, port


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
    """业务侧接入点：在本机 **被动监听** WebSocket；**允许多个 PatchBay 同时连入**。

    ``send()`` 将同一帧 **广播** 到当前所有已连接 PatchBay（同一序号 ``seq``），由各交换机各自按路由转发。

    构造为 ``Jack(port[, host=...])``：默认 ``host=0.0.0.0``；在 ``host:port`` 上挂 ``ws_path``（默认 ``/ws``）。
    各 PatchBay 配置里该机 ``address`` 须为对端可达的 ``host:port``。

    可选 ``listeners``：``JackListener`` 子类列表（同步回调）。
    """

    def __init__(
        self,
        port: int,
        *,
        host: str = "0.0.0.0",
        ws_path: str = "/ws",
        listeners: Sequence[JackListener] | None = None,
    ) -> None:
        if not (0 <= port <= 65535):
            raise ValueError(f"port must be 0..65535, got {port}")
        h = str(host).strip()
        if not h:
            raise ValueError("host must be non-empty")
        self._bind_host = h
        self._bind_port = port
        self._ws_path = ws_path if ws_path.startswith("/") else f"/{ws_path}"
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None
        self._eff_host: str | None = None
        self._eff_port: int | None = None
        self._peers: list[web.WebSocketResponse] = []
        self._ws_lock = asyncio.Lock()
        self._seq = itertools.count(1)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._handlers: list[PacketHandler] = []
        self._listeners: list[JackListener] = list(listeners or ())
        self._aclose_done = False
        self._stopped = asyncio.Event()

    @property
    def listen_address(self) -> str:
        """本 Jack 用于填入 PatchBay 的 ``host:port`` 提示；须先 ``await start()``。

        若绑定在 ``0.0.0.0``，此处为 ``127.0.0.1:port`` 便于本机互通；跨机请在配置中写真实网卡 IP。
        """
        if self._eff_host is None or self._eff_port is None:
            raise RuntimeError("listen_address is only available after start()")
        h = self._eff_host
        if h == "0.0.0.0":
            h = "127.0.0.1"
        if ":" in h and not h.startswith("["):
            return f"[{h}]:{self._eff_port}"
        return f"{h}:{self._eff_port}"

    def build_application(self) -> web.Application:
        """构建含 WebSocket 路由的 aiohttp 应用；供测试嵌入或自定义挂载。"""
        app = web.Application()
        app.router.add_get(self._ws_path, self._handle_ws)
        return app

    async def _handle_ws(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        async with self._ws_lock:
            self._peers.append(ws)
        emit_jack_listeners(self._listeners, "on_link_up")
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.BINARY:
                    try:
                        frame = decode_frame(msg.data)
                    except Exception:
                        logger.exception("Jack %r invalid frame", self.listen_address)
                        continue
                    await self._dispatch_frame(frame)
                elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.ERROR):
                    break
        finally:
            async with self._ws_lock:
                try:
                    self._peers.remove(ws)
                except ValueError:
                    pass
            emit_jack_listeners(self._listeners, "on_link_down")
        return ws

    async def start(self) -> None:
        """在本机绑定并开始接受 PatchBay 的入站 WebSocket。"""
        if self._runner is not None:
            return
        self._aclose_done = False
        self._stopped.clear()
        self._loop = asyncio.get_running_loop()
        app = self.build_application()
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, self._bind_host, self._bind_port)
        await self._site.start()
        eff_h, eff_p = _effective_listen_host_port(self._site, self._bind_host, self._bind_port)
        self._eff_host = eff_h
        self._eff_port = eff_p

    async def join(self) -> None:
        """阻塞直至 `aclose()` 完成。"""
        await self._stopped.wait()

    async def run(self) -> None:
        """等价于 ``start()`` + 阻塞直至退出信号或主任务取消 + ``aclose()``。"""
        await self.start()
        try:
            await wait_until_interrupt()
        except asyncio.CancelledError:
            raise
        finally:
            await self.aclose()

    async def aclose(self) -> None:
        """停止监听并关闭当前链路。"""
        if self._aclose_done:
            return
        self._aclose_done = True
        emit_jack_listeners(self._listeners, "on_stopping")
        async with self._ws_lock:
            to_close = list(self._peers)
            self._peers.clear()
        for w in to_close:
            if not w.closed:
                try:
                    await w.close()
                except Exception:
                    logger.debug("Jack: close peer WebSocket failed", exc_info=True)
        if self._site is not None:
            await self._site.stop()
            self._site = None
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None
        self._eff_host = None
        self._eff_port = None
        self._stopped.set()

    def register(self, fn: PacketHandler) -> PacketHandler:
        """显式注册收包回调；与 ``jack(fn)`` / ``@jack`` 等价。"""
        self._handlers.append(fn)
        return fn

    def __call__(self, fn: PacketHandler) -> PacketHandler:
        """``@jack`` 或 ``jack(handler)`` 注册回调，等价于 ``register``。"""
        return self.register(fn)

    async def send(self, packet: object) -> None:
        """向当前所有已连接的 PatchBay **广播** 同一帧业务数据包（同一 ``seq``）。"""
        try:
            data = encode_application_packet(packet)
        except TypeError:
            raise
        except Exception:
            logger.exception("Jack %r: 无法编码数据包", self.listen_address)
            return
        seq = next(self._seq)
        frame = Frame(kind="send", payload=data, seq=seq)
        raw = encode_frame(frame)
        async with self._ws_lock:
            targets = [w for w in self._peers if not w.closed]
        if not targets:
            logger.warning("Jack %r: send dropped (no PatchBay connected)", self.listen_address)
            emit_jack_listeners(self._listeners, "on_send_dropped", "not_connected")
            return
        results = await asyncio.gather(
            *[t.send_bytes(raw) for t in targets],
            return_exceptions=True,
        )
        failures = sum(1 for r in results if isinstance(r, BaseException))
        if failures:
            ex = next((r for r in results if isinstance(r, BaseException)), None)
            logger.warning(
                "Jack %r: broadcast send failures %s/%s to PatchBay peers",
                self.listen_address,
                failures,
                len(targets),
                exc_info=ex if isinstance(ex, Exception) else None,
            )
            if failures == len(targets):
                emit_jack_listeners(self._listeners, "on_send_failed")

    def send_sync(self, packet: object) -> None:
        """同步发送；需在已有事件循环的上下文中使用。"""
        loop = self._loop
        if loop is None:
            raise RuntimeError("call start() before send_sync()")
        fut = asyncio.run_coroutine_threadsafe(self.send(packet), loop)
        fut.result(timeout=30.0)

    async def _dispatch_frame(self, frame: Frame) -> None:
        if frame.kind == "hello":
            return
        if frame.kind == "deliver" and frame.payload is not None:
            emit_jack_listeners(self._listeners, "on_incoming_deliver", frame.payload)
            await self._emit_payload_parallel(frame.payload)
        elif frame.kind == "error" and frame.payload is not None:
            msg = frame.payload.decode("utf-8", errors="replace")
            logger.error("PatchBay error for %s: %s", self.listen_address, msg)
            emit_jack_listeners(self._listeners, "on_patchbay_error", msg)
        elif frame.kind == "ack" and frame.seq is not None:
            emit_jack_listeners(self._listeners, "on_ack", frame.seq)
            logger.debug("Jack %s ack seq=%s", self.listen_address, frame.seq)

    async def _emit_payload_parallel(self, payload: bytes) -> None:
        if not self._handlers:
            return
        try:
            decoded = decode_application_packet(payload)
        except Exception:
            logger.error("Jack %r 无法解码数据包（非合法 msgpack 负载）", self.listen_address, exc_info=True)
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
                    self.listen_address,
                    i,
                    exc_info=(type(res), res, res.__traceback__),
                )
