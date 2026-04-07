import logging
from typing import Any
from automation.hub import Hub
from automation.core.entity import entity_registry
from automation.core.event import event_registry
from automation.core.condition import condition_registry
from automation.core.action import action_registry
from automation.core.trigger import trigger_registry

logger = logging.getLogger(__name__)

SECTION_TO_REGISTRIES = {
    "entities": entity_registry,
    "events": event_registry,
    "conditions": condition_registry,
    "actions": action_registry,
    "triggers": trigger_registry,
}

DEFAULT_TYPES: dict[str, str] = {
    "conditions": "expression",
    "triggers": "trigger",
}


def build_section(
    section_name: str, section_data: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    registry = SECTION_TO_REGISTRIES[section_name]
    default_type = DEFAULT_TYPES.get(section_name)
    result = {}
    for name, spec in section_data.items():
        spec = dict(spec)
        type_name = spec.pop("type", default_type)
        if type_name is None:
            raise ValueError(f"{section_name}.{name} missing required field 'type'")
        cls = registry.get(type_name)
        result[name] = cls(instance_name=name, **spec)
    return result


async def load(hub: Hub, config: dict[str, Any]) -> None:
    built: dict[str, dict[str, Any]] = {}
    for section_name in hub.SECTIONS:
        data = config.get(section_name, {})
        built[section_name] = build_section(section_name, data)

    old_config = hub.config
    old_sections = {name: getattr(hub, name) for name in hub.SECTIONS}

    hub.config = config
    for section_name, items in built.items():
        setattr(hub, section_name, items)

    activated: list[tuple[str, str]] = []
    try:
        for section_name in hub.SECTIONS:
            for obj in hub.section(section_name).values():
                await obj.on_validate(hub)

        for section_name in hub.SECTIONS:
            for name, obj in hub.section(section_name).items():
                await obj.on_activate(hub)
                activated.append((section_name, name))
    except Exception:
        for sec, n in reversed(activated):
            try:
                await hub.section(sec)[n].on_stop()
            except Exception:
                logger.exception("Cleanup failed for %s.%s", sec, n)
        hub.config = old_config
        for section_name, items in old_sections.items():
            setattr(hub, section_name, items)
        raise