from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from onebot_protocol import MessagePayload

MessageCallback = Callable[[MessagePayload], Awaitable[None]]
VoidCallback = Callable[[], Awaitable[None]]
DisconnectCallback = Callable[[str], Awaitable[None]]
ErrorCallback = Callable[[BaseException], Awaitable[None]]


@dataclass
class Listener:
    """按事件名挂接异步回调；未赋值的槽位不参与派发。

    构造适配器时传入列表，与运行期登记的消息回调可同时存在。
    """

    on_message: MessageCallback | None = None
    """收到已转为统一消息载荷的入站聊天消息。"""
    on_start: VoidCallback | None = None
    """适配器开始监听或进入常驻运行。"""
    on_stop: VoidCallback | None = None
    """适配器停止监听或常驻运行结束。"""
    on_ready: VoidCallback | None = None
    """平台侧会话就绪，可稳定收发。"""
    on_connect: VoidCallback | None = None
    """底层传输已连通，未必已完成鉴权。"""
    on_disconnect: DisconnectCallback | None = None
    """传输断开；参数为平台给出的原因短句。"""
    on_error: ErrorCallback | None = None
    """连接或运行期未捕获的异常。"""


async def emit_void(listeners: list[Listener], name: str) -> None:
    """对监听器列表派发无参生命周期类回调。

    Args:
        listeners: 适配器持有的监听器实例
        name: 监听器上对应的无参槽位名
    """
    for listener in listeners:
        cb = getattr(listener, name, None)
        if cb is None:
            continue
        try:
            await cb()
        except Exception:
            pass


async def emit_disconnect(listeners: list[Listener], reason: str) -> None:
    """对监听器列表派发断开回调。

    Args:
        listeners: 适配器持有的监听器实例
        reason: 断开原因，供日志或重连策略使用
    """
    for listener in listeners:
        if listener.on_disconnect is None:
            continue
        try:
            await listener.on_disconnect(reason)
        except Exception:
            pass


async def emit_error(listeners: list[Listener], exc: BaseException) -> None:
    """对监听器列表派发错误回调。

    Args:
        listeners: 适配器持有的监听器实例
        exc: 本次错误对象
    """
    for listener in listeners:
        if listener.on_error is None:
            continue
        try:
            await listener.on_error(exc)
        except Exception:
            pass


async def emit_message(listeners: list[Listener], payload: MessagePayload) -> None:
    """对监听器列表派发消息回调。

    Args:
        listeners: 适配器持有的监听器实例
        payload: 已转换为对外统一格式的入站消息
    """
    for listener in listeners:
        if listener.on_message is None:
            continue
        try:
            await listener.on_message(payload)
        except Exception:
            pass
