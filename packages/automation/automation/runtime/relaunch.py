from __future__ import annotations

import logging
import os
import subprocess
import sys
import time

logger = logging.getLogger(__name__)


def relaunch_current_process() -> None:
    """
    用同一解释器与同一启动参数表启动新进程，并结束当前进程。

    Windows 下用子进程非阻塞拉起后立刻退出当前进程；POSIX 优先在同进程槽位上执行替换。
    """
    argv = [sys.executable, *sys.argv]
    logger.info("♻️ 正在重启进程: %s", argv)

    if sys.platform == "win32":
        subprocess.Popen(
            argv,
            close_fds=False,
            cwd=os.getcwd(),
        )
        os._exit(0)

    os.execv(sys.executable, argv)


def schedule_process_relaunch(*, delay: float = 0.0) -> None:
    """
    在事件循环空闲时执行重启，避免卡在异步栈中间。

    若无运行中的 asyncio 循环（例如极少数同步场景），则直接同步重启。
    """
    import asyncio

    def fire() -> None:
        try:
            relaunch_current_process()
        except Exception:
            logger.exception("进程重启失败")

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        if delay > 0:
            time.sleep(delay)
        fire()
        return

    if delay > 0:
        loop.call_later(delay, fire)
    else:
        loop.call_soon(fire)
