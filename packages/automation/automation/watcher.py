from __future__ import annotations
import asyncio
import logging
from pathlib import Path
from typing import Callable, Awaitable, Any, Union
from automation.hub import Hub, State

logger = logging.getLogger(__name__)


async def _interruptible_sleep(hub: Hub, seconds: float) -> bool:
    """返回 True 表示被中断（应退出），False 表示正常超时"""
    try:
        await asyncio.wait_for(hub.stop_event.wait(), timeout=seconds)
        return True
    except asyncio.TimeoutError:
        return False


async def watch_loop(
    hub: Hub,
    path: Path,
    on_change: Callable[[Union[str, Path, dict]], Awaitable[Any]],
    interval: float = 2.0,
    debounce: float = 0.5,
) -> None:
    last_mtime: float = 0
    while hub.state == State.RUNNING:
        try:
            mtime = path.stat().st_mtime
            if mtime > last_mtime:
                if last_mtime > 0:
                    if await _interruptible_sleep(hub, debounce):
                        return
                    mtime = path.stat().st_mtime
                    logger.info("Config changed, reloading: %s", path)
                    try:
                        await on_change(path)
                    except Exception:
                        logger.exception("Config reload failed")
                last_mtime = mtime
        except FileNotFoundError:
            pass
        if await _interruptible_sleep(hub, interval):
            return