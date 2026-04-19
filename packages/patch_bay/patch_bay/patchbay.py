from __future__ import annotations

import asyncio
import errno
import logging
import signal
import sys
import threading
from collections.abc import Mapping, Sequence
from typing import Any

import aiohttp
from aiohttp import ClientWebSocketResponse
from aiohttp.client_exceptions import ClientConnectorError
from express_evaluator import Evaluator

from .listeners import PatchBayListener, emit_listeners
from .peer import ws_url_for_jack_listen
from .protocol import Frame, decode_frame, encode_frame
from .routing import PatchBayConfig, RoutingTable, patch_bay_config_from_dict
from .rule_eval import rule_allows

logger = logging.getLogger(__name__)


def _is_expected_dial_failure(exc: BaseException) -> bool:
    """对端未监听或暂不可达；重连时不应刷 ERROR/traceback。"""
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError, ConnectionRefusedError)):
        return True
    if isinstance(exc, ClientConnectorError):
        return True
    if isinstance(exc, OSError):
        if sys.platform == "win32" and getattr(exc, "winerror", None) == 1225:
            return True
        e = exc.errno
        if e in (
            errno.ECONNREFUSED,
            errno.ENETUNREACH,
            errno.EHOSTUNREACH,
            errno.ETIMEDOUT,
        ):
            return True
    return False


class PatchBay:
    """中央交换：按配置 **主动连接** 各 Jack 的 WebSocket，在 Jack 之间转发字节流。"""

    def __init__(
        self,
        config: Mapping[str, Any],
        listeners: Sequence[PatchBayListener] | None = None,
    ) -> None:
        cfg = patch_bay_config_from_dict(dict(config))
        self._route_lock = threading.RLock()
        self._config = cfg
        self._routing = RoutingTable.from_config(cfg)
        self._evaluator = Evaluator()
        self._listeners: list[PatchBayListener] = list(listeners or ())
        self._clients: dict[str, ClientWebSocketResponse] = {}
        self._loop: asyncio.AbstractEventLoop | None = None
        self._shutdown = asyncio.Event()
        self._out_session: aiohttp.ClientSession | None = None
        self._out_tasks: list[asyncio.Task[None]] = []
        self._aclose_done = False

    @property
    def config(self) -> PatchBayConfig:
        with self._route_lock:
            return self._config

    def apply_config(self, config: Mapping[str, Any]) -> None:
        """用新的配置 dict 整体替换（线程安全）；运行中重连策略未实现，宜在启动前定稿。"""
        cfg = patch_bay_config_from_dict(dict(config))
        loop = self._loop
        if loop is None:
            self._apply_config(cfg)
            return
        loop.call_soon_threadsafe(self._apply_config, cfg)

    def _apply_config(self, cfg: PatchBayConfig) -> None:
        with self._route_lock:
            self._config = cfg
            self._routing = RoutingTable.from_config(cfg)

    async def serve(self) -> None:
        """为每个 Jack 启动出站连接任务，直到 ``aclose()``。"""
        self._aclose_done = False
        self._loop = asyncio.get_running_loop()
        self._shutdown.clear()
        self._out_session = aiohttp.ClientSession()
        with self._route_lock:
            jacks = list(self._config.jacks)
        for j in jacks:
            t = asyncio.create_task(self._maintain_jack(j.name, j.address), name=f"patchbay->{j.name}")
            self._out_tasks.append(t)
        await self._shutdown.wait()

    async def run(self) -> None:
        """等价于 ``serve()``：阻塞直至 ``aclose()`` 或信号 / 取消。"""
        loop = asyncio.get_running_loop()
        handlers: list[int] = []

        def _interrupt() -> None:
            self._shutdown.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _interrupt)
                handlers.append(sig)
            except (NotImplementedError, RuntimeError, ValueError, OSError):
                pass
        try:
            await self.serve()
        except asyncio.CancelledError:
            self._shutdown.set()
            raise
        finally:
            for sig in handlers:
                try:
                    loop.remove_signal_handler(sig)
                except Exception:
                    pass
            await self.aclose()

    async def aclose(self) -> None:
        """停止出站任务并关闭会话。"""
        if self._aclose_done:
            return
        self._aclose_done = True
        emit_listeners(self._listeners, "on_listen_stopping")
        self._shutdown.set()
        for t in self._out_tasks:
            t.cancel()
        for t in self._out_tasks:
            try:
                await t
            except asyncio.CancelledError:
                pass
        self._out_tasks.clear()
        if self._out_session is not None:
            await self._out_session.close()
            self._out_session = None
        with self._route_lock:
            self._clients.clear()

    async def _maintain_jack(self, name: str, address: str) -> None:
        session = self._out_session
        assert session is not None
        backoff = 0.5
        max_backoff = 30.0
        while not self._shutdown.is_set():
            url = ws_url_for_jack_listen(address)
            try:
                async with session.ws_connect(url, autoping=True) as ws:
                    with self._route_lock:
                        self._clients[name] = ws
                    emit_listeners(self._listeners, "on_jack_connected", name, address)
                    await self._send_hello(ws)
                    backoff = 0.5
                    try:
                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.BINARY:
                                try:
                                    frame = decode_frame(msg.data)
                                except Exception:
                                    logger.exception("invalid frame from jack %s", name)
                                    continue
                                if frame.kind == "send" and frame.payload is not None:
                                    await self._forward_send(name, frame.payload, frame.seq)
                            elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.ERROR):
                                break
                    finally:
                        with self._route_lock:
                            if self._clients.get(name) is ws:
                                del self._clients[name]
                        emit_listeners(self._listeners, "on_jack_disconnected", name)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                if _is_expected_dial_failure(e):
                    pass
                else:
                    logger.exception("outbound WebSocket to jack %r (%s) failed", name, address)
            if self._shutdown.is_set():
                break
            delay = min(backoff, max_backoff)
            try:
                await asyncio.wait_for(self._shutdown.wait(), timeout=delay)
                break
            except asyncio.TimeoutError:
                pass
            backoff = min(backoff * 2, max_backoff)

    async def _send_hello(self, ws: ClientWebSocketResponse) -> None:
        await ws.send_bytes(encode_frame(Frame(kind="hello")))

    async def _forward_send(
        self,
        from_jack: str,
        payload: bytes,
        seq: int | None,
    ) -> None:
        emit_listeners(self._listeners, "on_incoming_send", from_jack, payload, seq)
        with self._route_lock:
            candidates = list(self._routing.iter_from_jack(from_jack))
            clients = dict(self._clients)
        for w in candidates:
            if not rule_allows(w.expression, payload, self._evaluator):
                emit_listeners(
                    self._listeners,
                    "on_route_skipped",
                    from_jack,
                    w.to_jack,
                    payload,
                    reason="rule",
                )
                continue
            target_ws = clients.get(w.to_jack)
            if target_ws is None or target_ws.closed:
                emit_listeners(
                    self._listeners,
                    "on_route_skipped",
                    from_jack,
                    w.to_jack,
                    payload,
                    reason="offline",
                )
                continue
            deliver = Frame(kind="deliver", payload=payload)
            try:
                await target_ws.send_bytes(encode_frame(deliver))
                emit_listeners(
                    self._listeners,
                    "on_packet_delivered",
                    from_jack,
                    w.to_jack,
                    payload,
                )
            except Exception as exc:
                emit_listeners(
                    self._listeners,
                    "on_deliver_failed",
                    from_jack,
                    w.to_jack,
                    payload,
                    exc,
                )
                logger.warning("deliver to %s failed", w.to_jack, exc_info=True)
        if seq is not None:
            src = clients.get(from_jack)
            if src is not None and not src.closed:
                try:
                    await src.send_bytes(encode_frame(Frame(kind="ack", seq=seq)))
                except Exception:
                    logger.debug("ack to %s failed", from_jack, exc_info=True)
