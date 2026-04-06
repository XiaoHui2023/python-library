import ast
import re
from typing import ClassVar

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
    _type: ClassVar[str] = "entity_expression"

    expr: str
    _tree = PrivateAttr(default=None)
    _compiled = PrivateAttr(default=None)
    _placeholders = PrivateAttr(default_factory=dict)
    _ctx = PrivateAttr(default=None)

    def validate(self, ctx) -> None:
        self._ctx = ctx
        self._build_ast()

    def check(self) -> bool:
        return self._eval_expr()

    def _build_ast(self) -> None:
        parsed_expr, placeholders = self._prepare_expr(self.expr)

        try:
            tree = ast.parse(parsed_expr, mode="eval")
        except SyntaxError as e:
            raise ValueError(f"表达式语法错误: {self.expr!r}") from e

        self._validate_ast(tree)

        self._tree = tree
        self._compiled = compile(tree, "<entity_expression>", "eval")
        self._placeholders = placeholders

    def _prepare_expr(self, expr: str) -> tuple[str, dict[str, str]]:
        placeholders: dict[str, str] = {}

        def replace(match):
            path = match.group(1).strip()
            self._validate_entity_path(path)
            name = f"_v{len(placeholders)}"
            placeholders[name] = path
            return name

        parsed_expr = PLACEHOLDER_RE.sub(replace, expr)
        return parsed_expr, placeholders

    def _resolve_path(self, path: str):
        if "." not in path:
            raise ValueError(f"表达式变量必须是 '{{实体名.属性}}' 形式: {path!r}")

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

    def _validate_entity_path(self, path: str) -> None:
        self._resolve_path(path)

    def _validate_ast(self, tree: ast.AST) -> None:
        for node in ast.walk(tree):
            if not isinstance(node, ALLOWED_AST_MODS):
                raise ValueError(f"表达式包含不允许的语法: {type(node).__name__}")

    def _eval_expr(self) -> bool:
        values = {}
        for var_name, path in self._placeholders.items():
            values[var_name] = self._resolve_path(path)

        result = eval(self._compiled, {"__builtins__": {}}, values)
        if not isinstance(result, bool):
            raise ValueError(f"表达式结果必须是 bool，实际得到 {type(result).__name__}")
        return result