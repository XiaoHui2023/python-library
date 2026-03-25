from __future__ import annotations
from .job import Job
from pydantic import BaseModel, PrivateAttr
import asyncio
import logging
import time

logger = logging.getLogger(__name__)

class Scheduler(BaseModel):
    """调度器，轮询所有 Job 并在条件满足时执行"""

    interval: float = 1.0
    """轮询间隔，单位：秒"""
    _running: bool = PrivateAttr(default=False)
    """是否正在运行"""

    async def run(self):
        """异步主循环"""
        self._running = True
        logger.info("Scheduler 启动")
        try:
            while self._running:
                jobs = Job.get_all()
                if not jobs:
                    break
                tasks = [
                    job.run()
                    for job in jobs
                    if job.should_run()
                ]
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                await asyncio.sleep(self.interval)
        except asyncio.CancelledError:
            pass
        finally:
            self._running = False
            logger.info("Scheduler 停止")

    def stop(self):
        self._running = False