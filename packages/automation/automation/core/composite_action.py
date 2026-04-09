from __future__ import annotations
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from automation.renderer import Renderer
    from automation.hub import Hub


class CompositeAction:
    """config 定义的可复用组合动作"""

    def __init__(
        self,
        name: str,
        params: dict[str, str],
        conditions: list[str],
        action_specs: list[dict],
    ):
        self.name = name
        self.params = params
        self.conditions = conditions
        self.action_specs = action_specs

    async def run(self, hub: Hub, renderer: Renderer, **kwargs: Any) -> None:
        from automation.executor import execute_action_spec

        missing = set(self.params) - set(kwargs)
        if missing:
            raise ValueError(
                f"Action {self.name!r} missing params: {missing}"
            )

        child_renderer = renderer.derive("action", "local", kwargs)

        for expr in self.conditions:
            if not child_renderer.eval_bool(expr):
                return

        for spec in self.action_specs:
            await execute_action_spec(spec, child_renderer, hub)

    def validate(self, hub: Hub) -> None:
        for expr in self.conditions:
            hub.renderer.validate_expr(expr)
        from automation.executor import validate_action_spec
        for spec in self.action_specs:
            validate_action_spec(spec, hub)