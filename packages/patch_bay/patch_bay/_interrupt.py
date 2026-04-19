from __future__ import annotations

import asyncio
import signal


async def wait_until_interrupt() -> None:
    """阻塞直至收到 SIGINT/SIGTERM（平台支持且已注册成功时），否则仅依赖协程被取消（如 ``asyncio.run`` 下 Ctrl+C）。

    若本机无法注册信号处理器，则一直挂起，直至外层任务 ``cancel``（与常见 ``asyncio.run`` 行为一致）。
    """
    loop = asyncio.get_running_loop()
    ev = asyncio.Event()
    registered: list[int] = []

    def _wake() -> None:
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
