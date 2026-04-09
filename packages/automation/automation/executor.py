from __future__ import annotations
from typing import Any, TYPE_CHECKING

from automation.core.action import action_registry

if TYPE_CHECKING:
    from automation.renderer import Renderer
    from automation.hub import Hub


async def execute_action_spec(
    spec: dict[str, Any],
    renderer: Renderer,
    hub: Hub,
) -> None:
    """统一执行一个 action spec dict"""
    spec = dict(spec)
    type_name = spec.pop("type")
    raw_params = spec

    rendered_params = renderer.render_value(raw_params)

    if type_name in hub.actions:
        composite = hub.actions[type_name]
        await composite.run(hub, renderer, **rendered_params)
        return

    action_cls = action_registry.get(type_name)
    action = action_cls(
        instance_name=f"_inline_{type_name}", **rendered_params
    )
    action._hub = hub
    await action.execute(renderer)


def validate_action_spec(spec: dict[str, Any], hub: Hub) -> None:
    """配置加载时校验 action spec 合法性"""
    if "type" not in spec:
        raise ValueError("Action spec missing required field 'type'")
    type_name = spec["type"]
    if type_name in hub.actions:
        return
    try:
        action_registry.get(type_name)
    except KeyError:
        raise ValueError(f"Unknown action type: {type_name!r}")