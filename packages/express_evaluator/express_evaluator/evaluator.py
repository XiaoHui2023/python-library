from __future__ import annotations

import ast
import operator
from collections.abc import Iterable, Mapping
from typing import Any
from .variable_logic import VARIABLE_RE, replace_placeholders
from .errors import (
    ExpressionSyntaxError,
    UndefinedVariableError,
    UnsafeExpressionError,
)
from .registry import SyntaxSpec, get_syntaxs
from .syntax import load_syntax_modules
from .manifest import DEFAULT_SYNTAXS

_CORE_AST_NODES: tuple[type[ast.AST], ...] = (
    ast.Expression,
    ast.Name,
    ast.Load,
    ast.Store,
)

_COMPARE_OPS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.Is: operator.is_,
    ast.IsNot: operator.is_not,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
}

class Evaluator:
    def __init__(
        self,
        syntaxs: list[str]=DEFAULT_SYNTAXS,
        strict_undefined: bool=True,
    ):
        """
        Args:
            syntaxs: 语法列表
            strict_undefined: 是否严格检查未定义变量
        """
        self.syntax_names = syntaxs
        self.strict_undefined = strict_undefined

        self.specs: list[SyntaxSpec] = []
        self.allowed_nodes: set[type[ast.AST]] = set(_CORE_AST_NODES)
        self.allowed_functions: dict[str, Any] = {}

        self._load_syntax()

    def _load_syntax(self):
        """加载语法"""
        # 加载语法模块
        load_syntax_modules()
        
        # 获取语法列表
        self.specs = get_syntaxs(self.syntax_names)

        for spec in self.specs:
            self.allowed_nodes.update(spec.ast_nodes)
            self.allowed_functions.update(spec.functions)

    def evaluate(self, expression: str, data: Mapping[str, Any]) -> Any:
        """表达式求值
        Args:
            expression: 表达式
            data: 数据
        Returns:
            求值结果
        """
        source = expression
        values: dict[str, Any] = {}

        if VARIABLE_RE.search(expression):
            source, values = replace_placeholders(
                expression,
                data,
                strict=self.strict_undefined,
            )

        try:
            tree = ast.parse(source, mode="eval")
        except SyntaxError as exc:
            raise ExpressionSyntaxError(f"Invalid expression: {expression!r}") from exc

        self._validate_ast(tree)
        return self._eval(tree.body, dict(values))

    def __call__(self, expression: str, data: Mapping[str, Any]) -> Any:
        return self.evaluate(expression, data)

    def _validate_ast(self, tree: ast.AST) -> None:
        """验证AST"""
        for node in ast.walk(tree):
            if not isinstance(node, tuple(self.allowed_nodes)):
                raise UnsafeExpressionError(
                    f"Unsupported syntax node: {type(node).__name__}"
                )

            if isinstance(node, ast.Call):
                if not isinstance(node.func, ast.Name):
                    raise UnsafeExpressionError("Only direct function calls are allowed")
                if node.func.id not in self.allowed_functions:
                    raise UnsafeExpressionError(
                        f"Function {node.func.id!r} is not enabled"
                    )
                if node.keywords:
                    raise UnsafeExpressionError("Keyword arguments are not supported")

            if isinstance(node, ast.Attribute):
                if node.attr.startswith("_"):
                    raise UnsafeExpressionError(
                        f"Private attribute access is not allowed: {node.attr!r}"
                    )

            if isinstance(node, ast.comprehension):
                if not isinstance(node.target, ast.Name):
                    raise UnsafeExpressionError(
                        "Only simple variable targets are allowed in comprehensions"
                    )
                if node.is_async:
                    raise UnsafeExpressionError("Async comprehensions are not supported")

    def _eval(self, node: ast.AST, env: dict[str, Any]) -> Any:
        """求值AST"""
        if isinstance(node, ast.Constant):
            return node.value

        if isinstance(node, ast.Name):
            if node.id in env:
                return env[node.id]
            raise UndefinedVariableError(f"Unknown variable: {node.id}")

        if isinstance(node, ast.List):
            return [self._eval(item, env) for item in node.elts]

        if isinstance(node, ast.Tuple):
            return tuple(self._eval(item, env) for item in node.elts)

        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                for value_node in node.values:
                    result = self._eval(value_node, env)
                    if not result:
                        return result
                return result
            if isinstance(node.op, ast.Or):
                for value_node in node.values:
                    result = self._eval(value_node, env)
                    if result:
                        return result
                return result
            raise UnsafeExpressionError(f"Unsupported boolean operator: {type(node.op).__name__}")

        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.Not):
                return not self._eval(node.operand, env)
            raise UnsafeExpressionError(f"Unsupported unary operator: {type(node.op).__name__}")

        if isinstance(node, ast.Compare):
            left = self._eval(node.left, env)
            for op, comparator in zip(node.ops, node.comparators):
                right = self._eval(comparator, env)
                func = _COMPARE_OPS.get(type(op))
                if func is None:
                    raise UnsafeExpressionError(
                        f"Unsupported comparison operator: {type(op).__name__}"
                    )
                if not func(left, right):
                    return False
                left = right
            return True

        if isinstance(node, ast.Attribute):
            target = self._eval(node.value, env)
            return self._read_member(target, node.attr)

        if isinstance(node, ast.ListComp):
            return list(self._iter_comprehension(node.generators, 0, node.elt, env))

        if isinstance(node, ast.GeneratorExp):
            return self._iter_comprehension(node.generators, 0, node.elt, env)

        if isinstance(node, ast.Call):
            func_name = node.func.id
            func = self.allowed_functions[func_name]
            args = [self._eval(arg, env) for arg in node.args]
            return func(*args)

        raise UnsafeExpressionError(f"Cannot evaluate AST node: {type(node).__name__}")

    def _iter_comprehension(
        self,
        generators: list[ast.comprehension],
        index: int,
        elt: ast.AST,
        env: dict[str, Any],
    ) -> Iterable[Any]:
        if index >= len(generators):
            yield self._eval(elt, env)
            return

        generator = generators[index]
        iterable = self._eval(generator.iter, env)
        target_name = generator.target.id

        for item in iterable:
            inner_env = dict(env)
            inner_env[target_name] = item

            passed = True
            for cond in generator.ifs:
                if not self._eval(cond, inner_env):
                    passed = False
                    break

            if not passed:
                continue

            yield from self._iter_comprehension(
                generators,
                index + 1,
                elt,
                inner_env,
            )

    def _read_member(self, value: Any, name: str) -> Any:
        if name.startswith("_"):
            raise UnsafeExpressionError(f"Private attribute access is not allowed: {name!r}")

        if isinstance(value, Mapping) and name in value:
            return value[name]

        if hasattr(value, name):
            return getattr(value, name)

        raise UndefinedVariableError(
            f"Cannot read attribute/key {name!r} from {type(value).__name__!r}"
        )