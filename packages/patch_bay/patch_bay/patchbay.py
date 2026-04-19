from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Mapping, Sequence
from typing import Any

import aiohttp
from aiohttp import web
from express_evaluator import Evaluator

from .listeners import PatchBayListener, emit_listeners
from .protocol import Frame, decode_frame, encode_frame, error_frame
from .routing import PatchBayConfig, RoutingTable, patch_bay_config_from_dict
from .rule_eval import rule_allows

logger = logging.getLogger(__name__)


LISTEN_HOST = "0.0.0.0"


def _effective_listen_host_port(site: web.BaseSite, host: str, port: int) -> tuple[str, int]:
    """若 ``port==0``，尽量从已绑定 socket 解析实际端口。"""
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


class PatchBay:
    """中央交换：按配置在 Jack 之间转发字节流（Jack 互不直连）；可选 ``PatchBayListener`` 接收内部事件。"""

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
        self._clients: dict[str, web.WebSocketResponse] = {}
        self._client_remote: dict[str, str] = {}
        self._loop: asyncio.AbstractEventLoop | None = None
        self._shutdown = asyncio.Event()
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None
        self._app: web.Application | None = None

    @property
    def config(self) -> PatchBayConfig:
        with self._route_lock:
            return self._config

    def apply_config(self, config: Mapping[str, Any]) -> None:
        """用新的配置 dict 整体替换（线程安全）。"""
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

    def build_application(self) -> web.Application:
        """构建仅含 WebSocket 路由的 aiohttp 应用；供测试或嵌入。"""
        return self._build_app()

    def _build_app(self) -> web.Application:
        app = web.Application()
        app[PATCH_BAY_APP_KEY] = self
        app.router.add_get("/ws", _handle_ws)
        self._app = app
        return app

    async def serve(self) -> None:
        """启动 WebSocket 服务，直到 aclose()。"""
        self._loop = asyncio.get_running_loop()
        self._shutdown.clear()
        app = self._build_app()
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        host = LISTEN_HOST
        port = self._config.listen
        self._site = web.TCPSite(self._runner, host, port)
        await self._site.start()
        eff_host, eff_port = _effective_listen_host_port(self._site, host, port)
        emit_listeners(self._listeners, "on_listen_started", eff_host, eff_port)
        logger.info("PatchBay WebSocket at ws://%s:%s/ws", eff_host, eff_port)
        await self._shutdown.wait()

    async def aclose(self) -> None:
        """停止服务。"""
        emit_listeners(self._listeners, "on_listen_stopping")
        self._shutdown.set()
        if self._site is not None:
            await self._site.stop()
            self._site = None
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None

    async def _handle_client_ws(self, request: web.Request, ws: web.WebSocketResponse) -> None:
        pb: PatchBay = request.app[PATCH_BAY_APP_KEY]
        jack_name: str | None = None
        try:
            msg = await ws.receive()
            if msg.type != aiohttp.WSMsgType.BINARY:
                await ws.send_bytes(encode_frame(error_frame("first frame must be binary hello")))
                await ws.close()
                return
            try:
                hello = decode_frame(msg.data)
            except Exception:
                await ws.send_bytes(encode_frame(error_frame("invalid hello frame")))
                await ws.close()
                return
            if hello.kind != "hello" or hello.jack is None:
                await ws.send_bytes(encode_frame(error_frame("first frame must be hello with jack")))
                await ws.close()
                return
            jack_name = hello.jack
            with pb._route_lock:
                if jack_name in pb._clients:
                    await ws.send_bytes(encode_frame(error_frame("jack name already connected")))
                    await ws.close()
                    return
                pb._clients[jack_name] = ws
                peer = request.remote or ""
                pb._client_remote[jack_name] = peer
            emit_listeners(pb._listeners, "on_jack_connected", jack_name, peer)

            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.BINARY:
                    try:
                        frame = decode_frame(msg.data)
                    except Exception:
                        logger.exception("invalid frame from %s", jack_name)
                        continue
                    if frame.kind == "send" and frame.payload is not None:
                        await pb._forward_send(jack_name, frame.payload, frame.seq)
                elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.ERROR):
                    break
        finally:
            if jack_name is not None:
                with pb._route_lock:
                    if pb._clients.get(jack_name) is ws:
                        del pb._clients[jack_name]
                        pb._client_remote.pop(jack_name, None)
                emit_listeners(pb._listeners, "on_jack_disconnected", jack_name)

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


PATCH_BAY_APP_KEY = web.AppKey[PatchBay]("patch_bay")


async def _handle_ws(request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    pb: PatchBay = request.app[PATCH_BAY_APP_KEY]
    await pb._handle_client_ws(request, ws)
    return ws
