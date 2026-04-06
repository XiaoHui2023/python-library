from typing import Any
from automation.context import AutomationContext
from automation.core.entity import entity_registry
from automation.core.event import event_registry
from automation.core.condition import condition_registry
from automation.core.action import action_registry
from automation.core.trigger import trigger_registry

SECTION_TO_REGISTRIES = {
    "entities": entity_registry,
    "events": event_registry,
    "conditions": condition_registry,
    "actions": action_registry,
    "triggers": trigger_registry,
}

def build_section(section_name: str, section_data: dict[str, dict[str, Any]]):
    registry = SECTION_TO_REGISTRIES[section_name]
    result = {}

    for name, spec in section_data.items():
        spec = dict(spec)
        try:
            type_name = spec.pop("type")
        except KeyError as e:
            raise ValueError(f"{section_name}.{name} 缺少 type") from e

        cls = registry.get(type_name)
        try:
            obj = cls(instance_name=name, **spec)
        except TypeError as e:
            raise ValueError(f"{section_name}.{name} 创建失败") from e

        result[name] = obj

    return result

def validate_all(ctx: AutomationContext) -> None:
    for section_name in SECTION_TO_REGISTRIES:
        for name, obj in ctx.section(section_name).items():
            try:
                obj.validate(ctx)
            except Exception as e:
                raise ValueError(f"{section_name}.{name} 校验失败: {e}") from e

def activate_all(ctx: AutomationContext) -> None:
    for section_name in SECTION_TO_REGISTRIES:
        for name, obj in ctx.section(section_name).items():
            try:
                obj.activate(ctx)
            except Exception as e:
                raise ValueError(f"{section_name}.{name} 激活失败: {e}") from e

def build_all(config: dict[str, Any]) -> AutomationContext:
    built = {}
    for section in SECTION_TO_REGISTRIES:
        built[section] = build_section(section, config.get(section, {}))

    ctx = AutomationContext(**built)
    validate_all(ctx)
    activate_all(ctx)
    return ctx