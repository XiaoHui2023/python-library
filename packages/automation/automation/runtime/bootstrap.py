from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
from typing import Any

from automation.core.base import BaseAutomation
from automation.core.entity import Entity
from automation.core.event import Event
from automation.core.trigger import Trigger
from automation.errors import AutomationLoadError, LoadErrorCode, LoadPhase
from automation.listener.events import LoadError
from automation.runtime.context import Context
from automation.runtime.global_state import get_context

logger = logging.getLogger(__name__)


async def teardown_automation(context: Context | None = None) -> None:
    """反激活各实例并卸总线桥接；再对各实例调用运行期收尾编排。"""

    ctx = context or get_context()
    for section_name in reversed(ctx.AUTOMATION_SECTIONS):
        for obj in list(ctx.section(section_name).values()):
            try:
                await obj.inactive_phase()
            except Exception:
                logger.exception(
                    "inactive_phase failed for %s.%s",
                    section_name,
                    getattr(obj, "instance_name", "?"),
                )
    ctx.detach_observer_bridge()
    ctx._on_state_changed.clear()
    ctx._event_fire_handlers.clear()
    for section_name in reversed(ctx.AUTOMATION_SECTIONS):
        for obj in list(ctx.section(section_name).values()):
            try:
                await obj.run_phase(closing=True)
            except Exception:
                logger.exception(
                    "run_phase(closing=True) failed for %s.%s",
                    section_name,
                    getattr(obj, "instance_name", "?"),
                )


def clear_partitions(context: Context | None = None) -> None:
    ctx = context or get_context()
    ctx.entities.clear()
    ctx.events.clear()
    ctx.triggers.clear()


async def activate_automation(context: Context | None = None) -> None:
    """对已填入各分区的对象执行 build → validate → activate。"""

    ctx = context or get_context()
    activated: list[tuple[str, str]] = []
    try:
        for section_name in ctx.AUTOMATION_SECTIONS:
            for obj in ctx.section(section_name).values():
                try:
                    await obj.build_phase()
                except AutomationLoadError:
                    raise
                except Exception as e:
                    err = AutomationLoadError(
                        section=section_name,
                        instance=obj.instance_name,
                        phase=LoadPhase.BUILD,
                        code=LoadErrorCode.BUILD_FAILED,
                        cause=e,
                    )
                    ctx.emit(
                        LoadError(
                            section_name,
                            obj.instance_name,
                            err.phase,
                            err.code,
                            e,
                        )
                    )
                    raise err from e

        for section_name in ctx.AUTOMATION_SECTIONS:
            for obj in ctx.section(section_name).values():
                try:
                    await obj.validate_phase()
                except AutomationLoadError:
                    raise
                except Exception as e:
                    err = AutomationLoadError(
                        section=section_name,
                        instance=obj.instance_name,
                        phase=LoadPhase.VALIDATE,
                        code=LoadErrorCode.VALIDATION_FAILED,
                        cause=e,
                    )
                    ctx.emit(
                        LoadError(
                            section_name,
                            obj.instance_name,
                            err.phase,
                            err.code,
                            e,
                        )
                    )
                    raise err from e

        for section_name in ctx.AUTOMATION_SECTIONS:
            for name, obj in ctx.section(section_name).items():
                await obj.activate_phase()
                activated.append((section_name, name))
    except Exception:
        for sec, n in reversed(activated):
            try:
                await ctx.section(sec)[n].inactive_phase()
            except Exception:
                logger.exception("Cleanup inactive_phase failed for %s.%s", sec, n)
        ctx.detach_observer_bridge()
        ctx._on_state_changed.clear()
        ctx._event_fire_handlers.clear()
        for sec, n in reversed(activated):
            try:
                await ctx.section(sec)[n].run_phase(closing=True)
            except Exception:
                logger.exception(
                    "Cleanup run_phase(closing=True) failed for %s.%s", sec, n
                )
        raise


async def reload_automation(
    *,
    entities: dict[str, Entity] | None = None,
    events: dict[str, Event] | None = None,
    triggers: dict[str, Trigger] | None = None,
    context: Context | None = None,
) -> None:
    """替换各分区注册表并重新激活（脚本或代码组装入口）。"""

    ctx = context or get_context()
    had = any(ctx.section(n) for n in ctx.AUTOMATION_SECTIONS)
    if had:
        await teardown_automation(ctx)

    clear_partitions(ctx)
    if entities is not None:
        ctx.entities = dict(entities)
    if events is not None:
        ctx.events = dict(events)
    if triggers is not None:
        ctx.triggers = dict(triggers)

    await activate_automation(ctx)


async def load_script(path: str | Path, *, context: Context | None = None) -> None:
    """执行自动化脚本模块；模块须定义 async def setup(ctx) 或 def setup(ctx)。"""

    ctx = context or get_context()
    script_path = Path(path).resolve()
    if not script_path.is_file():
        raise FileNotFoundError(script_path)

    spec = importlib.util.spec_from_file_location(
        f"automation_script_{script_path.stem}",
        script_path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load script: {script_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    setup = getattr(module, "setup", None)
    if setup is None:
        raise AttributeError(
            f"Script {script_path.name} must define setup(ctx: Context)"
        )

    had = any(ctx.section(n) for n in ctx.AUTOMATION_SECTIONS)
    if had:
        await teardown_automation(ctx)
    clear_partitions(ctx)

    result = setup(ctx)
    if hasattr(result, "__await__"):
        await result

    await activate_automation(ctx)


def register_entity(name: str, entity: Entity, *, context: Context | None = None) -> None:
    _register_partition("entities", name, entity, context=context)


def register_event(name: str, event: Event, *, context: Context | None = None) -> None:
    _register_partition("events", name, event, context=context)


def register_trigger(
    name: str, trigger: Trigger, *, context: Context | None = None
) -> None:
    _register_partition("triggers", name, trigger, context=context)


def _register_partition(
    section: str,
    name: str,
    obj: BaseAutomation,
    *,
    context: Context | None,
) -> None:
    ctx = context or get_context()
    if obj._ctx is not ctx:
        raise ValueError(
            f"{section}.{name}: object must be bound to the global context"
        )
    if obj.instance_name != name:
        raise ValueError(
            f"{section}.{name}: instance_name {obj.instance_name!r} "
            f"does not match registration key {name!r}"
        )
    ctx.section(section)[name] = obj
