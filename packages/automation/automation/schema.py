from __future__ import annotations
from typing import Any, TYPE_CHECKING

from automation.core.entity import (
    entity_registry, introspect_attributes, introspect_methods,
)
from automation.core.event import event_registry
from automation.core.action import action_registry
from automation.core.trigger import trigger_registry

if TYPE_CHECKING:
    from automation.hub import Hub

SECTION_REGISTRIES = {
    "entities": entity_registry,
    "events": event_registry,
    "actions": action_registry,
    "triggers": trigger_registry,
}


def _field_schema(field_info) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if field_info.annotation is not None:
        result["type"] = getattr(field_info.annotation, "__name__", str(field_info.annotation))
    if field_info.description:
        result["description"] = field_info.description
    if field_info.default is not None:
        result["default"] = field_info.default
    result["required"] = field_info.is_required()
    return result


def export_type_schema() -> dict[str, Any]:
    result: dict[str, Any] = {}

    for section, registry in SECTION_REGISTRIES.items():
        section_types = {}
        for reg_name in registry.get_registered_names():
            short = reg_name.split(".")[-1]
            cls = registry.get(short)

            config_fields = {}
            for name, field_info in cls.model_fields.items():
                if name == "instance_name":
                    continue
                config_fields[name] = _field_schema(field_info)

            type_info: dict[str, Any] = {"config_fields": config_fields}

            if section == "entities":
                type_info["attributes"] = [
                    {
                        "name": a.name, "type": a.type,
                        "description": a.description,
                        "readonly": a.readonly, "default": a.default,
                    }
                    for a in introspect_attributes(cls)
                ]
                type_info["methods"] = [
                    {
                        "name": m.name, "description": m.description,
                        "params": m.params, "return_type": m.return_type,
                    }
                    for m in introspect_methods(cls)
                ]

            section_types[short] = type_info
        result[section] = section_types

    result["composite_actions"] = {
        "description": "可复用的命名组合动作",
        "fields": {
            "params": {"type": "object", "description": "参数声明 {名称: 类型}"},
            "conditions": {"type": "array", "description": "条件表达式列表"},
            "actions": {"type": "array", "description": "子动作规格列表"},
        },
    }
    return result


def export_instance_schema(hub: Hub) -> dict[str, Any]:
    from automation.core.entity import Entity

    result: dict[str, Any] = {}

    entities = {}
    for name, entity in hub.entities.items():
        info: dict[str, Any] = {"type": entity._type}
        if isinstance(entity, Entity):
            info["attributes"] = {
                attr.name: {
                    "type": attr.type,
                    "value": getattr(entity, attr.name, None),
                    "readonly": attr.readonly,
                    "description": attr.description,
                }
                for attr in entity.get_attributes()
            }
            info["methods"] = [
                {
                    "name": m.name, "description": m.description,
                    "params": m.params, "return_type": m.return_type,
                }
                for m in entity.get_methods()
            ]
        entities[name] = info
    result["entities"] = entities

    events = {}
    for name, event in hub.events.items():
        event_info: dict[str, Any] = {"type": event._type}
        config = {}
        for fname, finfo in event.model_fields.items():
            if fname == "instance_name":
                continue
            config[fname] = getattr(event, fname)
        event_info["config"] = config
        events[name] = event_info
    result["events"] = events

    triggers = {}
    for name, trigger in hub.triggers.items():
        triggers[name] = {
            "type": trigger._type,
            "event": trigger.event,
            "mode": trigger.mode,
            "conditions": trigger.conditions,
            "actions_count": len(trigger.actions),
        }
    result["triggers"] = triggers

    actions = {}
    for name, composite in hub.actions.items():
        actions[name] = {
            "params": composite.params,
            "conditions": composite.conditions,
            "actions_count": len(composite.action_specs),
        }
    result["actions"] = actions

    return result