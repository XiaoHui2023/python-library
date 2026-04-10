import logging
from typing import Any
from .hub import Hub
from .core.entity import entity_registry
from .core.event import event_registry
from .core.trigger import trigger_registry
from .core.composite_action import CompositeAction
from .errors import ConfigLoadError, LoadPhase, LoadErrorCode

logger = logging.getLogger(__name__)

SECTION_TO_REGISTRIES = {
    "entities": entity_registry,
    "events": event_registry,
    "triggers": trigger_registry,
}

DEFAULT_TYPES: dict[str, str] = {
    "triggers": "trigger",
}


def build_section(section_name, section_data):
    registry = SECTION_TO_REGISTRIES[section_name]
    default_type = DEFAULT_TYPES.get(section_name)
    result = {}
    for name, spec in section_data.items():
        spec = dict(spec)
        type_name = spec.pop("type", default_type)
        if type_name is None:
            raise ConfigLoadError(
                section=section_name, instance=name,
                phase=LoadPhase.BUILD, code=LoadErrorCode.MISSING_TYPE,
            )
        try:
            cls = registry.get(type_name)
        except KeyError as e:
            raise ConfigLoadError(
                section=section_name, instance=name,
                phase=LoadPhase.BUILD, code=LoadErrorCode.UNKNOWN_TYPE,
                cause=e,
            ) from e
        try:
            result[name] = cls(instance_name=name, **spec)
        except Exception as e:
            raise ConfigLoadError(
                section=section_name, instance=name,
                phase=LoadPhase.BUILD, code=LoadErrorCode.INVALID_CONFIG,
                cause=e,
            ) from e
    return result


def build_actions(
    section_data: dict[str, dict[str, Any]]
) -> dict[str, CompositeAction]:
    result = {}
    for name, spec in section_data.items():
        spec = dict(spec)
        params = spec.get("params", {})
        conditions = spec.get("conditions", [])
        action_specs = spec.get("actions", [])
        if not action_specs:
            raise ValueError(
                f"actions.{name} must have at least one child action"
            )
        result[name] = CompositeAction(
            name=name,
            params=params,
            conditions=conditions,
            action_specs=action_specs,
        )
    return result


async def load(hub: Hub, config: dict[str, Any]) -> None:
    built: dict[str, dict[str, Any]] = {}
    for section_name in hub.AUTOMATION_SECTIONS:
        data = config.get(section_name, {})
        built[section_name] = build_section(section_name, data)

    built_actions = build_actions(config.get("actions", {}))

    old_config = hub.config
    old_sections = {
        name: getattr(hub, name) for name in hub.AUTOMATION_SECTIONS
    }
    old_actions = hub.actions

    hub.config = config
    for section_name, items in built.items():
        setattr(hub, section_name, items)
    hub.actions = built_actions

    activated: list[tuple[str, str]] = []
    try:
        for section_name in hub.AUTOMATION_SECTIONS:
            for obj in hub.section(section_name).values():
                obj._hub = hub
                try:
                    await obj.on_validate(hub)
                except ConfigLoadError:
                    raise
                except Exception as e:
                    err = ConfigLoadError(
                        section=section_name, instance=obj.instance_name,
                        phase=LoadPhase.VALIDATE,
                        code=LoadErrorCode.VALIDATION_FAILED, cause=e,
                    )
                    hub.notify("on_load_error", section_name,
                                obj.instance_name, err.phase, err.code, e)
                    raise err from e

        for composite in hub.actions.values():
            composite.validate(hub)

        for section_name in hub.AUTOMATION_SECTIONS:
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
        hub.actions = old_actions
        raise