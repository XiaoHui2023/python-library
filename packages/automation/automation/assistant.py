from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from configlib import load_config
from watch_config import WatchConfig

from automation.hub import Hub, State
from automation.core import Entity, Event, Trigger, BaseAutomation
from automation.core.composite_action import CompositeAction
from automation import loader, updater, schema
from automation.listeners import BaseListener

logger = logging.getLogger(__name__)


class Assistant:
    def __init__(self, listeners: list[BaseListener] | BaseListener | None = None) -> None:
        self._hub = Hub()
        if listeners is not None:
            if isinstance(listeners, BaseListener):
                listeners = [listeners]
            self._hub.listeners = listeners
        self._watcher: WatchConfig[dict] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._reload_lock = asyncio.Lock()

    @property
    def entities(self) -> dict[str, Entity]:
        return self._hub.entities

    @property
    def events(self) -> dict[str, Event]:
        return self._hub.events

    @property
    def actions(self) -> dict[str, CompositeAction]:
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
            raise TypeError(
                "watch=True requires a file path, dict is not supported"
            )
        config = _read_source(source)
        await loader.load(self._hub, config)
        if watch:
            self._watcher = WatchConfig(Path(source), dict)
            self._watcher(self._on_config_change)
        return self

    async def start(self) -> Assistant:
        if self._hub.state == State.RUNNING:
            return self
        self._hub.state = State.RUNNING
        self._hub.stop_event.clear()
        self._loop = asyncio.get_running_loop()
        for section_name in self._hub.AUTOMATION_SECTIONS:
            for obj in self._hub.section(section_name).values():
                await obj.on_start()
        if self._watcher is not None:
            self._watcher.start()
        self._hub.notify("on_start")
        return self

    async def run(self) -> Assistant:
        await self.start()
        await self._hub.stop_event.wait()
        return self

    async def stop(self) -> None:
        if self._hub.state != State.RUNNING:
            return
        self._hub.state = State.STOPPED
        if self._watcher:
            self._watcher.stop()
        for section_name in reversed(self._hub.AUTOMATION_SECTIONS):
            for obj in self._hub.section(section_name).values():
                await obj.on_stop()
        self._hub.stop_event.set()
        self._hub.notify("on_stop")

    async def update(self, source: str | Path | dict) -> None:
        """手动热更新"""
        new_config = _read_source(source)
        await self._apply_reload(new_config)

    def watch(self, path: str | Path, interval: float = 2.0) -> Assistant:
        """设置文件监控"""
        if self._watcher:
            self._watcher.stop()
        self._watcher = WatchConfig(Path(path), dict, interval=interval)
        self._watcher(self._on_config_change)
        if self._hub.state == State.RUNNING:
            self._watcher.start()
        return self

    def _on_config_change(self, cfg: dict, changelog) -> None:
        if self._loop is None or self._loop.is_closed():
            return
        asyncio.run_coroutine_threadsafe(
            self._apply_reload(cfg), self._loop
        )

    async def _apply_reload(self, new_config: dict) -> None:
        async with self._reload_lock:
            old_config = self._hub.config
            if old_config == new_config:
                return
            await updater.apply_diff(self._hub, old_config, new_config)
            self._hub.config = new_config

    @staticmethod
    def export_schema() -> dict:
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