from __future__ import annotations
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from automation.hub import Hub


def resolve_entity_path(path: str, hub: Hub) -> Any:
    entity_name, attr_path = path.split(".", 1)

    try:
        value = hub.entities[entity_name]
    except KeyError as e:
        raise ValueError(f"Entity {entity_name!r} not found") from e

    for part in attr_path.split("."):
        if not hasattr(value, part):
            raise ValueError(
                f"Entity {entity_name!r} has no attribute path {attr_path!r}"
            )
        value = getattr(value, part)

    return value


async def resolve_placeholder(
    token: str,
    hub: Hub,
    cache: dict[str, bool],
    stack: list[str],
) -> Any:
    if "." in token:
        return resolve_entity_path(token, hub)
    return await resolve_condition(token, hub, cache, stack)


async def resolve_condition(
    name: str,
    hub: Hub,
    cache: dict[str, bool],
    stack: list[str],
) -> bool:
    if name in cache:
        return cache[name]

    if name in stack:
        cycle = " -> ".join([*stack, name])
        raise ValueError(f"Circular condition dependency: {cycle}")

    try:
        condition = hub.conditions[name]
    except KeyError as e:
        raise ValueError(f"Condition {name!r} not found") from e

    from .condition import ExpressionCondition

    if isinstance(condition, ExpressionCondition):
        result = await condition.check_with_state(cache, stack)
    else:
        stack.append(name)
        try:
            result = await condition.check()
        finally:
            stack.pop()

    if not isinstance(result, bool):
        raise ValueError(
            f"Condition {name!r} must return bool, got {type(result).__name__}"
        )

    cache[name] = result
    return result