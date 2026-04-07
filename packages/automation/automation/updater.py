from __future__ import annotations

import logging
from typing import Any
from automation.hub import Hub, State
from automation.loader import build_section
from automation.changelog import ChangeLog

logger = logging.getLogger(__name__)


def _field_diffs(
    old_spec: dict | None, new_spec: dict | None
) -> dict[str, tuple[Any, Any]]:
    old_spec = old_spec or {}
    new_spec = new_spec or {}
    diffs: dict[str, tuple[Any, Any]] = {}
    for key in set(old_spec) | set(new_spec):
        old_val = old_spec.get(key)
        new_val = new_spec.get(key)
        if old_val != new_val:
            diffs[key] = (old_val, new_val)
    return diffs


async def apply_diff(
    hub: Hub, old: dict[str, Any], new: dict[str, Any]
) -> ChangeLog:
    changelog = ChangeLog()

    changed_refs: set[tuple[str, str]] = set()
    for section_name in hub.SECTIONS:
        old_section = old.get(section_name, {})
        new_section = new.get(section_name, {})
        for name in set(old_section) | set(new_section):
            if old_section.get(name) != new_section.get(name):
                changed_refs.add((section_name, name))

    for section_name in hub.SECTIONS:
        old_section = old.get(section_name, {})
        new_section = new.get(section_name, {})
        current = hub.section(section_name)

        for name in list(current):
            if name not in new_section:
                obj = current.pop(name)
                await obj.on_stop()
                changelog.removed(section_name, name)

        for name, spec in new_section.items():
            old_spec = old_section.get(name)
            if name in current and old_spec == spec:
                continue

            if name in current:
                obj = current[name]
                if hub.state == State.RUNNING:
                    await obj.on_stop()
                raw_spec = dict(spec)
                raw_spec.pop("type", None)
                await obj.update(hub, raw_spec)
                await obj.on_validate(hub)
                await obj.on_update(hub)
                await obj.on_activate(hub)
                if hub.state == State.RUNNING:
                    await obj.on_start()
                changelog.updated(section_name, name, _field_diffs(old_spec, spec))
            else:
                built = build_section(section_name, {name: spec})
                obj = built[name]
                await obj.on_validate(hub)
                await obj.on_activate(hub)
                current[name] = obj
                if hub.state == State.RUNNING:
                    await obj.on_start()
                changelog.added(section_name, name)

    for trigger in hub.triggers.values():
        refs = {
            ("events", trigger.event),
            *(("conditions", c) for c in trigger.conditions),
            *(("actions", a) for a in trigger.actions),
        }
        if refs & changed_refs:
            await trigger.on_validate(hub)
            await trigger.on_activate(hub)
            changelog.revalidated("triggers", trigger.instance_name)

    return changelog