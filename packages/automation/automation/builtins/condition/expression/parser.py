from __future__ import annotations
import ast
import re
import operator
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from automation.hub import Hub

PLACEHOLDER_RE = re.compile(r"\{([^{}]+)\}")

ALLOWED_AST_NODES = (
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

_CMP_OPS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Is: operator.is_,
    ast.IsNot: operator.is_not,
}

def _safe_eval(compiled_tree: ast.Expression, variables: dict) -> bool:
    """用 AST visitor 替代 eval，完全不执行任意代码"""
    return _eval_node(compiled_tree.body, variables)

def _eval_node(node: ast.AST, variables: dict):
    match node:
        case ast.Constant(value=value):
            return value
        case ast.Name(id=name):
            if name not in variables:
                raise ValueError(f"Unknown variable: {name!r}")
            return variables[name]
        case ast.UnaryOp(op=ast.Not(), operand=operand):
            return not _eval_node(operand, variables)
        case ast.BoolOp(op=ast.And(), values=values):
            return all(_eval_node(v, variables) for v in values)
        case ast.BoolOp(op=ast.Or(), values=values):
            return any(_eval_node(v, variables) for v in values)
        case ast.Compare(left=left, ops=ops, comparators=comparators):
            current = _eval_node(left, variables)
            for op, comparator in zip(ops, comparators):
                rhs = _eval_node(comparator, variables)
                if isinstance(op, ast.In):
                    if current not in rhs:
                        return False
                elif isinstance(op, ast.NotIn):
                    if current in rhs:
                        return False
                else:
                    fn = _CMP_OPS.get(type(op))
                    if fn is None:
                        raise ValueError(f"Unsupported operator: {type(op).__name__}")
                    if not fn(current, rhs):
                        return False
                current = rhs
            return True
        case _:
            raise ValueError(f"Unsupported AST node: {type(node).__name__}")

def validate_ast(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_AST_NODES):
            raise ValueError(f"Disallowed syntax in expression: {type(node).__name__}")


def validate_placeholder(token: str, hub: Hub) -> None:
    if "." in token:
        entity_name = token.split(".", 1)[0]
        if entity_name not in hub.entities:
            raise ValueError(f"Entity {entity_name!r} not found")
        return
    if token not in hub.conditions:
        raise ValueError(f"Condition {token!r} not found")


def parse_expr(
    expr: str,
    hub: Hub,
) -> tuple[Any, dict[str, str]]:
    """
    解析表达式字符串，返回 (compiled_code, placeholders)。
    placeholders: {变量名: 原始 token}
    """
    placeholders: dict[str, str] = {}

    def replace(match: re.Match) -> str:
        token = match.group(1).strip()
        validate_placeholder(token, hub)
        name = f"_v{len(placeholders)}"
        placeholders[name] = token
        return name

    parsed_expr = PLACEHOLDER_RE.sub(replace, expr)

    try:
        tree = ast.parse(parsed_expr, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"Syntax error in expression: {expr!r}") from e

    validate_ast(tree)
    return tree, placeholders