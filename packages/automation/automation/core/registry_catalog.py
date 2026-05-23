from __future__ import annotations

from typing import TYPE_CHECKING, Any

from registry import Registry

if TYPE_CHECKING:
    from automation.core.base import BaseAutomation
    from automation.runtime.context import Context

catalog_registry = Registry()

ENTITY_NAMESPACE = "entity"
EVENT_NAMESPACE = "event"
TRIGGER_NAMESPACE = "trigger"
ACTION_NAMESPACE = "action"

entity_registry = catalog_registry.namespace(ENTITY_NAMESPACE)
event_registry = catalog_registry.namespace(EVENT_NAMESPACE)
trigger_registry = catalog_registry.namespace(TRIGGER_NAMESPACE)
action_registry = catalog_registry.namespace(ACTION_NAMESPACE)

_NAMESPACE_ALIASES: dict[str, str] = {
    "entities": ENTITY_NAMESPACE,
    "events": EVENT_NAMESPACE,
    "triggers": TRIGGER_NAMESPACE,
    "actions": ACTION_NAMESPACE,
}

_PARTITION_REGISTRY: dict[str, Registry] = {
    ENTITY_NAMESPACE: entity_registry,
    EVENT_NAMESPACE: event_registry,
    TRIGGER_NAMESPACE: trigger_registry,
    ACTION_NAMESPACE: action_registry,
}


def _resolve_namespace(namespace: str) -> str:
    key = namespace.strip()
    return _NAMESPACE_ALIASES.get(key, key)


def _partition_registry(namespace: str) -> Registry:
    resolved = _resolve_namespace(namespace)
    try:
        return _PARTITION_REGISTRY[resolved]
    except KeyError as e:
        known = ", ".join(sorted(_PARTITION_REGISTRY))
        raise ValueError(
            f"未知分区 {namespace!r}（解析为 {resolved!r}），已知: {known}"
        ) from e


def instantiate_registered(
    namespace: str,
    kind: str,
    instance_name: str,
    ctx: Context,
    spec: dict[str, Any],
) -> BaseAutomation:
    """按分区与注册键查找类型并例化。

    Args:
        namespace: 分区名（如 entity / entities，与配置分区或 *_NAMESPACE 一致）。
        kind: 注册表中的实现键（配置 type 或 registered_kind）。
        instance_name: 实例名。
        ctx: 运行时上下文。
        spec: 构造参数字典（可含 type，会在例化前剔除）。

    Returns:
        已绑定上下文的自动化对象实例。
    """
    from automation.core.base import BaseAutomation

    partition = _partition_registry(namespace)
    cls = partition.get(kind)
    if not isinstance(spec, dict):
        raise TypeError("spec 须为字典")
    fields = dict(spec)
    fields.pop("ctx", None)
    fields.pop("type", None)
    obj = cls(instance_name=instance_name, _ctx=ctx, **fields)
    if not isinstance(obj, BaseAutomation):
        raise TypeError(
            f"{cls.__name__} 须为 BaseAutomation 子类，得到 {type(obj).__name__}"
        )
    return obj
