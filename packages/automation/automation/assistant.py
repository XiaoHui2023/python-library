from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from configlib import load_config
from automation.hub import Hub, State
from automation.core import Entity, Event, Condition, Action, Trigger, BaseAutomation
from automation.changelog import ChangeLog
from automation import loader, updater, watcher, schema

logger = logging.getLogger(__name__)


class Assistant:
    """自动化管家 — 统一入口"""

    def __init__(self) -> None:
        self._hub = Hub()
        self._watch_task: asyncio.Task | None = None
        self._watch_path: Path | None = None
        self._watch_interval: float = 2.0

    @property
    def entities(self) -> dict[str, Entity]:
        return self._hub.entities

    @property
    def events(self) -> dict[str, Event]:
        return self._hub.events

    @property
    def conditions(self) -> dict[str, Condition]:
        return self._hub.conditions

    @property
    def actions(self) -> dict[str, Action]:
        return self._hub.actions

    @property
    def triggers(self) -> dict[str, Trigger]:
        return self._hub.triggers

    def section(self, name: str) -> dict[str, BaseAutomation]:
        return self._hub.section(name)

    async def load(
        self, source: str | Path | dict, watch: bool = False
    ) -> Assistant:
        if watch and isinstance(source, dict):
            raise TypeError("watch=True requires a file path, dict is not supported")
        config = _read_source(source)
        await loader.load(self._hub, config)
        if watch:
            self._watch_path = Path(source)  # type: ignore[arg-type]
        return self

    async def start(self) -> Assistant:
        if self._hub.state == State.RUNNING:
            return self
        self._hub.state = State.RUNNING
        self._hub.stop_event.clear()
        for section_name in self._hub.SECTIONS:
            for obj in self._hub.section(section_name).values():
                await obj.on_start()
        if self._watch_path is not None:
            self._start_watch()
        logger.info("Assistant started")
        return self

    async def run(self) -> Assistant:
        """运行"""
        await self.start()
        await self._hub.stop_event.wait()
        return self

    async def stop(self) -> None:
        if self._hub.state != State.RUNNING:
            return
        self._hub.state = State.STOPPED
        if self._watch_task and not self._watch_task.done():
            self._watch_task.cancel()
        for section_name in reversed(self._hub.SECTIONS):
            for obj in self._hub.section(section_name).values():
                await obj.on_stop()
        self._hub.stop_event.set()
        logger.info("Assistant stopped")

    async def update(self, source: str | Path | dict) -> ChangeLog:
        """热更新"""
        new_config = _read_source(source)
        old_config = self._hub.config
        changelog = await updater.apply_diff(self._hub, old_config, new_config)
        self._hub.config = new_config
        if not changelog.is_empty:
            logger.info("\n%s", changelog.format())
        return changelog

    def watch(self, path: str | Path, interval: float = 2.0) -> Assistant:
        """文件监控"""
        self._watch_path = Path(path)
        self._watch_interval = interval
        if self._hub.state == State.RUNNING:
            self._start_watch()
        return self

    def _start_watch(self) -> None:
        if self._watch_task and not self._watch_task.done():
            self._watch_task.cancel()
        self._watch_task = asyncio.ensure_future(
            watcher.watch_loop(
                self._hub,
                self._watch_path,  # type: ignore[arg-type]
                self.update,
                self._watch_interval,
            )
        )

    @staticmethod
    def export_schema() -> dict:
        """导出 schema"""
        return schema.export_schema()


def _read_source(source: str | Path | dict) -> dict[str, Any]:
    if isinstance(source, (str, Path)):
        data = load_config(str(source))
        if not isinstance(data, dict):
            raise TypeError(
                f"Config root must be a dict, got {type(data).__name__}"
            )
        return data
    return source