import ast
import re
from typing import Any, ClassVar

from pydantic import PrivateAttr
from automation.core import Condition

PLACEHOLDER_RE = re.compile(r"\{([^{}]+)\}")

ALLOWED_AST_MODS = (
    ast.Expression,
    ast.BoolOp,
    ast.UnaryOp,
    ast.Compare,
    ast.Name,
    ast.Constant,
    ast.And,
    ast.Or,
    ast.Not,
    ast.Eq,
    ast.NotEq,
    ast.Gt,
    ast.GtE,
    ast.Lt,
    ast.LtE,
    ast.Is,
    ast.IsNot,
    ast.In,
    ast.NotIn,
    ast.Load,
)

class ExpressionCondition(Condition):
    _abstract: ClassVar[bool] = False
    _type: ClassVar[str] = "expression"

    expr: str
    _tree = PrivateAttr(default=None)
    _compiled = PrivateAttr(default=None)
    _placeholders = PrivateAttr(default_factory=dict)
    _ctx = PrivateAttr(default=None)

    def validate(self, ctx) -> None:
        self._ctx = ctx
        self._build_ast()

    def check(self) -> bool:
        return self._check_with_state({}, [])

    def _build_ast(self) -> None:
        parsed_expr, placeholders = self._prepare_expr(self.expr)

        try:
            tree = ast.parse(parsed_expr, mode="eval")
        except SyntaxError as e:
            raise ValueError(f"表达式语法错误: {self.expr!r}") from e

        self._validate_ast(tree)

        self._tree = tree
        self._compiled = compile(tree, "<expression>", "eval")
        self._placeholders = placeholders

    def _prepare_expr(self, expr: str) -> tuple[str, dict[str, str]]:
        placeholders: dict[str, str] = {}

        def replace(match):
            token = match.group(1).strip()
            self._validate_placeholder(token)
            name = f"_v{len(placeholders)}"
            placeholders[name] = token
            return name

        parsed_expr = PLACEHOLDER_RE.sub(replace, expr)
        return parsed_expr, placeholders

    def _resolve_entity_path(self, path: str) -> Any:
        entity_name, attr_path = path.split(".", 1)

        try:
            value = self._ctx.entities[entity_name]
        except KeyError as e:
            raise ValueError(f"实体 {entity_name!r} 不存在") from e

        for part in attr_path.split("."):
            if not hasattr(value, part):
                raise ValueError(f"实体 {entity_name!r} 不存在属性路径 {attr_path!r}")
            value = getattr(value, part)

        return value

    def _resolve_condition(
        self,
        name: str,
        cache: dict[str, bool],
        stack: list[str],
    ) -> bool:
        if name in cache:
            return cache[name]

        if name in stack:
            cycle = " -> ".join([*stack, name])
            raise ValueError(f"条件循环依赖: {cycle}")

        try:
            condition = self._ctx.conditions[name]
        except KeyError as e:
            raise ValueError(f"条件 {name!r} 不存在") from e

        if isinstance(condition, ExpressionCondition):
            result = condition._check_with_state(cache, stack)
        else:
            stack.append(name)
            try:
                result = condition.check()
            finally:
                stack.pop()

        if not isinstance(result, bool):
            raise ValueError(f"条件 {name!r} 的结果必须是 bool，实际得到 {type(result).__name__}")

        cache[name] = result
        return result

    def _resolve_placeholder(
        self,
        token: str,
        cache: dict[str, bool],
        stack: list[str],
    ) -> Any:
        if "." in token:
            return self._resolve_entity_path(token)
        return self._resolve_condition(token, cache, stack)

    def _validate_placeholder(self, token: str) -> None:
        if "." in token:
            self._resolve_entity_path(token)
            return

        if token not in self._ctx.conditions:
            raise ValueError(f"条件 {token!r} 不存在")

    def _validate_ast(self, tree: ast.AST) -> None:
        for node in ast.walk(tree):
            if not isinstance(node, ALLOWED_AST_MODS):
                raise ValueError(f"表达式包含不允许的语法: {type(node).__name__}")

    def _eval_expr(self, cache: dict[str, bool], stack: list[str]) -> bool:
        values = {}
        for var_name, token in self._placeholders.items():
            values[var_name] = self._resolve_placeholder(token, cache, stack)

        result = eval(self._compiled, {"__builtins__": {}}, values)
        if not isinstance(result, bool):
            raise ValueError(f"表达式结果必须是 bool，实际得到 {type(result).__name__}")
        return result

    def _check_with_state(self, cache: dict[str, bool], stack: list[str]) -> bool:
        name = self.instance_name
        if name in cache:
            return cache[name]

        if name in stack:
            cycle = " -> ".join([*stack, name])
            raise ValueError(f"条件循环依赖: {cycle}")

        stack.append(name)
        try:
            result = self._eval_expr(cache, stack)
        finally:
            stack.pop()

        cache[name] = result
        return result