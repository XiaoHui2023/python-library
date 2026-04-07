from __future__ import annotations

from typing import ClassVar, TYPE_CHECKING, Any

from pydantic import PrivateAttr

from automation.core import Event

if TYPE_CHECKING:
    from automation.hub import Hub


class ScheduledEvent(Event):
    _abstract: ClassVar[bool] = True

    _job: Any = PrivateAttr(default=None)

    def _create_job(self) -> Any:
        raise NotImplementedError

    async def on_activate(self, hub: Hub) -> None:
        if self._job:
            await self._job.stop()
        job = self._create_job()
        job.add(self.fire)
        self._job = job

    async def on_start(self) -> None:
        if self._job:
            await self._job.start()

    async def on_stop(self) -> None:
        if self._job:
            await self._job.stop()