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
    """在端口交给系统挑选时，解析实际对外监听的主机与端口。

    Args:
        site: 已由 Web 框架启动、可用于读取底层套接字信息的站点对象。
        host: 绑定请求里声明的主机名。
        port: 绑定请求里声明的端口；非零时不做额外探测。

    Returns:
        对外宣告可用的主机与端口；端口为零且能读到套接字信息时返回系统选定值。
    """
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
    """去掉仅服务于类型检查器的元数据包装，保留参与载荷匹配的内层类型。

    Args:
        ann: 可能带有编辑器或校验附加信息的注解对象。

    Returns:
        若存在此类包装则返回其内层类型信息，否则原样返回。
    """
    o = get_origin(ann)
    if o is Annotated:
        return get_args(ann)[0]
    return ann


def _is_union_origin(o: Any) -> bool:
    """判断注解在运行时的「起源」是否表示多种类型的并集（含可选语义）。

    Args:
        o: 对注解执行「取起源」后的返回值。

    Returns:
        起源表示并集时为真。
    """
    if o is Union:
        return True
    ut = getattr(types, "UnionType", None)
    return ut is not None and o is ut


def _match_one(ann: Any, decoded: Any) -> tuple[bool, Any]:
    """按单条类型注解校验入站载荷是否满足处理器契约，并给出可传入的值。

    覆盖并集（含可选）、任意类型、可校验模型、常见容器、数据类与普通类型等；
    不满足时写日志并指示不要调用用户处理器。

    Args:
        ann: 单条形参注解（已去掉元数据包装）。
        decoded: 已从二进制帧还原的应用层对象。

    Returns:
        二元组：前者为真表示应调度用户处理器；后者为传入处理器的参数（前者为假时
        后者无业务意义）。
    """
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
            "Jack 收包与回调形参类型不符：无法匹配并集分支，实际类型为 %s",
            type(decoded).__name__,
        )
        return False, None
    if ann is Any:
        return True, decoded
    if isinstance(ann, type) and issubclass(ann, BaseModel):
        try:
            return True, ann.model_validate(decoded)
        except ValidationError as e:
            logger.error("Jack 收包与回调形参类型不符（模型校验失败）：%s", e)
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
                logger.error("Jack 收包与回调形参类型不符（数据类构造失败）：%s", e)
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
    """结合处理器首个形参的类型注解，决定是否向其投递解码结果。

    Args:
        fn: 用户注册的收包回调（同步或协程均可）。
        decoded: 已从应用层载荷解码得到的 Python 对象。

    Returns:
        是否应调用该回调，以及调用时应传入的参数（语义与类型匹配管线一致）。
    """
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
    """业务侧接入点：在本机被动接受交换节点的长连接。

    允许多个交换节点同时接入；出站时向当前所有已连接节点广播同一业务帧（共享
    序号），由各节点按各自路由策略转发。不与其他同类接入点建立直连。

    典型用法：绑定本机地址与端口（可选零端口由系统分配），在配置里把对端可达的
    监听地址写入交换节点后启动服务。
    """

    def __init__(
        self,
        port: int,
        *,
        host: str = "0.0.0.0",
        ws_path: str = "/ws",
        listeners: Sequence[JackListener] | None = None,
    ) -> None:
        """初始化监听参数与空的连接、处理器集合。

        Args:
            port: 监听端口；为零表示交给操作系统挑选可用端口。
            host: 绑定主机；空字符串非法。
            ws_path: 长连接路径；应以斜杠开头（否则自动补上）。
            listeners: 同步事件监听器序列；缺省为无。

        Raises:
            ValueError: 端口超出合法范围，或主机名为空。
        """
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
        """供写入交换侧配置的主机与端口文本（IPv6 时含方括号约定）。

        Returns:
            主机、端口组成的可配置字符串。

        Raises:
            RuntimeError: 在尚未成功启动监听前访问。
        """
        if self._eff_host is None or self._eff_port is None:
            raise RuntimeError("须先启动监听再读取监听地址")
        h = self._eff_host
        if h == "0.0.0.0":
            h = "127.0.0.1"
        if ":" in h and not h.startswith("["):
            return f"[{h}]:{self._eff_port}"
        return f"{h}:{self._eff_port}"

    def build_application(self) -> web.Application:
        """构造仅含本节点长连接路由的小型 Web 应用，便于嵌入测试或自定义挂载。

        Returns:
            已注册长连接路由的应用实例。
        """
        app = web.Application()
        app.router.add_get(self._ws_path, self._handle_ws)
        return app

    async def _handle_ws(self, request: web.Request) -> web.WebSocketResponse:
        """接受单条来自交换节点的长连接：收包、解码、分发，并在断开时清理登记。

        Args:
            request: 进入的、即将升级为长连接的 HTTP 请求。

        Returns:
            已结束生命周期的长连接响应对象。
        """
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
        """在本机绑定并开始接受交换节点的入站长连接。

        幂等：已启动时直接返回。

        Returns:
            无。
        """
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
        emit_jack_listeners(self._listeners, "on_listen_started", self.listen_address)

    async def join(self) -> None:
        """阻塞直至关闭流程结束（与主动关闭方法配对使用）。

        Returns:
            无。
        """
        await self._stopped.wait()

    async def run(self) -> None:
        """启动监听，随后阻塞至常见中断意图或任务取消，最后回收资源。

        Raises:
            CancelledError: 外层任务被取消时原样向上传递。
        """
        await self.start()
        try:
            await wait_until_interrupt()
        except asyncio.CancelledError:
            raise
        finally:
            await self.aclose()

    async def aclose(self) -> None:
        """停止监听、断开对端并释放底层 Web 服务资源；可安全重复调用。

        Returns:
            无。
        """
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
        """注册收包处理器；支持装饰器写法。

        Args:
            fn: 同步或异步回调；首个位置参数接收解码后的载荷。

        Returns:
            传入的同一可调用对象，便于链式装饰器。
        """
        self._handlers.append(fn)
        return fn

    def __call__(self, fn: PacketHandler) -> PacketHandler:
        """以实例本身作为装饰器注册收包回调，语义与显式注册相同。

        Args:
            fn: 待注册的收包回调。

        Returns:
            传入的同一可调用对象，便于链式装饰器。
        """
        return self.register(fn)

    async def send(self, packet: object) -> None:
        """将业务载荷编码后广播给当前所有已连接的交换节点（共享帧序号）。

        编码失败或当前无连接时写日志并通知监听器；类型不被支持时仍按语言惯例
        抛出类型错误。

        Args:
            packet: 映射、可校验声明式模型、数据类实例等，详见包内编码器约定。

        Raises:
            TypeError: 载荷类型不被编码器支持时。
        """
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
            logger.warning("Jack %r: 已丢弃发送（无交换节点连接）", self.listen_address)
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
                "Jack %r: 向交换节点广播发送失败 %s/%s",
                self.listen_address,
                failures,
                len(targets),
                exc_info=ex if isinstance(ex, Exception) else None,
            )
            if failures == len(targets):
                emit_jack_listeners(self._listeners, "on_send_failed")

    def send_sync(self, packet: object) -> None:
        """在已有事件循环线程上，以阻塞方式完成一次与异步发送方法等价的投递。

        Args:
            packet: 与异步发送方法相同的业务载荷。

        Raises:
            RuntimeError: 尚未完成监听启动、没有可用事件循环时。
        """
        loop = self._loop
        if loop is None:
            raise RuntimeError("须先启动监听再使用同步发送")
        fut = asyncio.run_coroutine_threadsafe(self.send(packet), loop)
        fut.result(timeout=30.0)

    async def _dispatch_frame(self, frame: Frame) -> None:
        """按帧语义分支：投递业务载荷、记录交换侧错误或确认发送序号。

        Args:
            frame: 已由有线层解码的一帧。

        Returns:
            无。
        """
        if frame.kind == "hello":
            return
        if frame.kind == "deliver" and frame.payload is not None:
            emit_jack_listeners(self._listeners, "on_incoming_deliver", frame.payload)
            await self._emit_payload_parallel(frame.payload)
        elif frame.kind == "error" and frame.payload is not None:
            msg = frame.payload.decode("utf-8", errors="replace")
            logger.error("交换节点报错（%s）：%s", self.listen_address, msg)
            emit_jack_listeners(self._listeners, "on_patchbay_error", msg)
        elif frame.kind == "ack" and frame.seq is not None:
            emit_jack_listeners(self._listeners, "on_ack", frame.seq)
            logger.debug("Jack %s ack seq=%s", self.listen_address, frame.seq)

    async def _emit_payload_parallel(self, payload: bytes) -> None:
        """并行调度所有已注册处理器；同步回调放入默认线程池。

        Args:
            payload: 仍为一帧中的应用层二进制块，将在内层解码。

        Returns:
            无。
        """
        if not self._handlers:
            return
        try:
            decoded = decode_application_packet(payload)
        except Exception:
            logger.error("Jack %r 无法解码数据包（非合法 msgpack 负载）", self.listen_address, exc_info=True)
            return
        loop = asyncio.get_running_loop()

        async def _one(h: PacketHandler) -> None:
            """对单个处理器做一次类型校验与调用；同步回调走线程池。

            Args:
                h: 当前待调度的收包处理器。

            Returns:
                无。
            """
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
