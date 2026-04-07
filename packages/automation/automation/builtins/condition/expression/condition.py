from __future__ import annotations
from typing import ClassVar, TYPE_CHECKING, Any

from pydantic import PrivateAttr
from automation.core import Condition

from .parser import parse_expr, _safe_eval
from .resolver import resolve_placeholder

if TYPE_CHECKING:
    from automation.hub import Hub


class ExpressionCondition(Condition):
    _abstract: ClassVar[bool] = False
    _type: ClassVar[str] = "expression"

    expr: str
    _compiled: Any = PrivateAttr(default=None)
    _placeholders: dict[str, str] = PrivateAttr(default_factory=dict)
    _hub: Hub | None = PrivateAttr(default=None)

    async def on_validate(self, hub: Hub) -> None:
        self._hub = hub
        self._compiled, self._placeholders = parse_expr(self.expr, hub)

    async def check(self) -> bool:
        return await self.check_with_state({}, [])

    async def check_with_state(self, cache: dict[str, bool], stack: list[str]) -> bool:
        name = self.instance_name
        if name in cache:
            return cache[name]
        if name in stack:
            cycle = " -> ".join([*stack, name])
            raise ValueError(f"Circular condition dependency: {cycle}")
        stack.append(name)
        try:
            result = await self._eval_expr(cache, stack)
        finally:
            stack.pop()
        cache[name] = result
        return result

    async def _eval_expr(self, cache: dict[str, bool], stack: list[str]) -> bool:
        values = {}
        for var_name, token in self._placeholders.items():
            values[var_name] = await resolve_placeholder(token, self._hub, cache, stack)
        result = _safe_eval(self._compiled, values)
        if not isinstance(result, bool):
            raise ValueError(
                f"Expression must return bool, got {type(result).__name__}"
            )
        return result