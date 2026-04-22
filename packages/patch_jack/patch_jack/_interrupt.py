from __future__ import annotations

import asyncio
import signal


async def wait_until_interrupt() -> None:
    """阻塞直至收到常见终端中断/温和退出意图，或直至外层取消当前协程。

    在运行环境允许把「用户中断」与「进程退出」挂到事件循环时，会据此唤醒等待；
    若环境不支持，则一直等到当前任务被取消（例如在仅支持取消、不暴露信号绑定的宿主中）。

    Returns:
        无。

    Raises:
        CancelledError: 等待期间若当前任务被取消，则按事件循环惯例原样向外传播。
    """
    loop = asyncio.get_running_loop()
    ev = asyncio.Event()
    registered: list[int] = []

    def _wake() -> None:
        """在进程级退出或用户中断被投递到循环时，解除主等待。"""
        ev.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _wake)
            registered.append(sig)
        except (NotImplementedError, RuntimeError, ValueError, OSError):
            pass

    try:
        await ev.wait()
    except asyncio.CancelledError:
        raise
    finally:
        for sig in registered:
            try:
                loop.remove_signal_handler(sig)
            except Exception:
                pass
