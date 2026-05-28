from __future__ import annotations

import asyncio
import logging

from automation.context import Context
from automation.automation import _instances

logger = logging.getLogger(__name__)

_ctx: Context | None = None


async def start() -> None:
    global _ctx
    if _ctx is not None and _ctx.is_running:
        return

    ctx = Context()
    ctx.stop_event = asyncio.Event()
    ctx.is_running = True
    _ctx = ctx

    for automation in _instances:
        automation.ctx = ctx

    for automation in _instances:
        await automation.on_init()

    timing_tasks = [
        asyncio.create_task(
            automation.run_timing_loop(),
            name=f"timing:{automation.name}",
        )
        for automation in _instances
    ]
    try:
        await ctx.stop_event.wait()
    finally:
        for task in timing_tasks:
            if not task.done():
                task.cancel()
        if timing_tasks:
            await asyncio.gather(*timing_tasks, return_exceptions=True)
        ctx.is_running = False


async def stop() -> None:
    ctx = _ctx
    if ctx is None or not ctx.is_running:
        return
    ctx.is_running = False
    ctx.stop_event.set()
    for automation in _instances:
        worker = getattr(automation, "_worker_task", None)
        if worker is not None and not worker.done():
            worker.cancel()
            try:
                await worker
            except asyncio.CancelledError:
                pass


async def run() -> None:
    try:
        await start()
    finally:
        await stop()


__all__ = ["run", "start", "stop"]
