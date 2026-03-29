from __future__ import annotations
from typing import ClassVar, Callable
from datetime import datetime
import asyncio
import logging
from pydantic import BaseModel, ConfigDict, PrivateAttr, Field

logger = logging.getLogger(__name__)


class Job(BaseModel):
    """任务调度基类"""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    when: Callable[[], bool] | None = Field(default=None, exclude=True)
    "自定义条件函数"
    max_runs: int | None = None
    "最大运行次数"
    immediate: bool = False
    """注册后立即执行一次"""
    fn: Callable | None = Field(default=None, exclude=True)

    _registry: ClassVar[list[Job]] = []

    _last_run: datetime | None = PrivateAttr(default=None)
    _run_count: int = PrivateAttr(default=0)
    _running: bool = PrivateAttr(default=False)

    def __call__(self, func: Callable) -> Callable:
        """作为装饰器，注册函数并创建独立的任务条目"""
        clone = self.model_copy()
        clone.fn = func
        clone._last_run = datetime.now()
        clone._run_count = 0
        clone._running = False
        Job._registry.append(clone)
        logger.debug(f"注册任务 {clone}")
        return func

    def should_run(self) -> bool:
        """判断是否应该运行，子类重载"""
        if self._running:
            return False
        if self.max_runs is not None and self._run_count >= self.max_runs:
            return False
        if self.when is not None and not self.when():
            return False
        return True

    async def run(self):
        """异步执行"""
        try:
            self._last_run = datetime.now()
            self._run_count += 1
            self._running = True
            if self.fn:
                if asyncio.iscoroutinefunction(self.fn):
                    await self.fn()
                else:
                    self.fn()
        except Exception as e:
            logger.exception(f"执行失败:{self}")
        finally:
            self._running = False
            # 耗尽完成次数
            if self.max_runs is not None and self._run_count >= self.max_runs:
                self.remove()
    
    def remove(self):
        """从注册表移除"""
        self._registry[:] = [j for j in self._registry if j is not self]

    @classmethod
    def get_all(cls) -> list[Job]:
        return list(cls._registry)

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.fn.__name__}>"



