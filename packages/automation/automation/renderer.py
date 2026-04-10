import ast
import re
import operator
from typing import Any
from .hub import Hub

VARIABLE_RE = re.compile(r"\{([^{}]+)\}")
_SINGLE_VAR_RE = re.compile(r"^\{([^{}]+)\}$")

class Renderer:
    """
    渲染器 — 统一的变量解析、模板渲染、表达式求值引擎
    
    通过 derive() 创建子渲染器来注入局部作用域，
    不可变设计，derive 不影响父渲染器。
    """

    def __init__(self, hub):
        self._hub: Hub = hub
        self._scopes: dict[tuple[str, str], dict[str, Any]] = {}

    def derive(self, type_: str, scope: str, data: dict[str, Any]) -> "Renderer":
        """创建带有新作用域的子渲染器"""
        child = Renderer.__new__(Renderer)
        child._hub = self._hub
        child._scopes = {**self._scopes, (type_, scope): data}
        return child

    # ── 变量解析 ──

    def resolve(self, token: str) -> Any:
        """解析 type.scope.attr_path 变量"""
        parts = token.split(".", 2)

        if len(parts) == 2:
            type_, scope = parts
            if type_ == "entity":
                if scope not in self._hub.entities:
                    raise ValueError(f"Entity {scope!r} not found")
                return self._hub.entities[scope]
            key = (type_, scope)
            if key in self._scopes:
                return self._scopes[key]
            raise ValueError(f"Cannot resolve variable: {{{token}}}")

        if len(parts) < 2:
            raise ValueError(
                f"Invalid variable: {{{token}}}, "
                f"expected {{type.scope.attribute}}"
            )
        type_, scope, attr_path = parts

        # 局部作用域: event.local.xxx, action.local.xxx
        key = (type_, scope)
        if key in self._scopes:
            return self._deep_get(self._scopes[key], attr_path)

        # 全局: entity.instance_name.attr_path
        if type_ == "entity":
            return self._resolve_entity(scope, attr_path)

        raise ValueError(f"Cannot resolve variable: {{{token}}}")

    def render(self, template: str) -> str:
        """将 {var} 占位符替换为实际值的字符串"""
        def replace(match):
            token = match.group(1).strip()
            return str(self.resolve(token))
        return VARIABLE_RE.sub(replace, template)

    def render_value(self, value: Any) -> Any:
        """递归解析值：纯变量引用返回原始对象，混合文本做字符串渲染"""
        if isinstance(value, str):
            m = _SINGLE_VAR_RE.match(value.strip())
            if m:
                return self.resolve(m.group(1).strip())
            return self.render(value)
        if isinstance(value, dict):
            return {k: self.render_value(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.render_value(v) for v in value]
        return value

    def eval_bool(self, expr: str) -> bool:
        """解析并求值布尔表达式，{var} 占位符会先解析为值"""
        placeholders: dict[str, str] = {}
        def replace(match):
            token = match.group(1).strip()
            name = f"_v{len(placeholders)}"
            placeholders[name] = token
            return name
        parsed = VARIABLE_RE.sub(replace, expr)
        tree = ast.parse(parsed, mode="eval")
        _validate_ast(tree)
        values = {
            name: self.resolve(token)
            for name, token in placeholders.items()
        }
        result = _safe_eval(tree.body, values)
        if not isinstance(result, bool):
            raise ValueError(
                f"Expression must return bool, got {type(result).__name__}"
            )
        return result

    def validate_token(self, token: str) -> None:
        parts = token.split(".", 2)
        if len(parts) < 2:
            raise ValueError(f"Invalid variable format: {{{token}}}")

        if len(parts) == 2:
            type_, scope = parts
            if type_ == "entity":
                if scope not in self._hub.entities:
                    raise ValueError(f"Entity {scope!r} not found")
                return
            if type_ in ("event", "action") and scope == "local":
                return
            raise ValueError(f"Unknown variable namespace: {type_}.{scope}")

        type_, scope, attr_path = parts
        if type_ == "entity":
            if scope not in self._hub.entities:
                raise ValueError(f"Entity {scope!r} not found")
            entity = self._hub.entities[scope]
            attr_root = attr_path.split(".")[0]
            known = {a.name for a in entity.get_attributes()}
            if attr_root not in known:
                raise ValueError(
                    f"Entity {scope!r} has no attribute {attr_root!r}, "
                    f"available: {', '.join(sorted(known))}"
                )
            return
        if type_ in ("event", "action") and scope == "local":
            return
        raise ValueError(f"Unknown variable namespace: {type_}.{scope}")

    def validate_template(self, template: str) -> None:
        for match in VARIABLE_RE.finditer(template):
            self.validate_token(match.group(1).strip())

    def validate_expr(self, expr: str) -> None:
        self.validate_template(expr)
        
        cleaned = VARIABLE_RE.sub("True", expr)
        try:
            tree = ast.parse(cleaned, mode="eval")
        except SyntaxError as e:
            raise ValueError(f"Syntax error in expression: {expr!r}") from e
        _validate_ast(tree)

    def _resolve_entity(self, name: str, attr_path: str) -> Any:
        if name not in self._hub.entities:
            raise ValueError(f"Entity {name!r} not found")
        entity = self._hub.entities[name]
        parts = attr_path.split(".")

        values = entity.get_attribute_values()
        first = parts[0]
        if first not in values:
            raise ValueError(
                f"{entity.__class__.__name__} {name!r} has no attribute path {attr_path!r}"
            )
        obj = values[first]

        for part in parts[1:]:
            if not hasattr(obj, part):
                raise ValueError(
                    f"{entity.__class__.__name__} {name!r} has no attribute path {attr_path!r}"
                )
            obj = getattr(obj, part)
        return obj

    @staticmethod
    def _deep_get(data: dict, path: str) -> Any:
        """从 dict 中按 . 分隔路径取值"""
        current = data
        for part in path.split("."):
            if isinstance(current, dict):
                if part not in current:
                    raise ValueError(f"Key {part!r} not found in scope data")
                current = current[part]
            else:
                if not hasattr(current, part):
                    raise ValueError(f"Attribute {part!r} not found")
                current = getattr(current, part)
        return current

_SAFE_NODES = (
    ast.Expression, ast.BoolOp, ast.Compare, ast.UnaryOp,
    ast.Constant, ast.Name, ast.Load, ast.Store, ast.And, ast.Or, ast.Not,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.Is, ast.IsNot, ast.In, ast.NotIn,
    ast.List, ast.Tuple,
    ast.Call,
    ast.Attribute,
    ast.ListComp, ast.GeneratorExp, ast.comprehension,
)
_SAFE_FUNCTIONS = frozenset({"any", "all"})

_CMP_OPS = {
    ast.Eq: operator.eq, ast.NotEq: operator.ne,
    ast.Lt: operator.lt, ast.LtE: operator.le,
    ast.Gt: operator.gt, ast.GtE: operator.ge,
    ast.Is: operator.is_, ast.IsNot: operator.is_not,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
}

def _validate_ast(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, _SAFE_NODES):
            raise ValueError(f"Unsupported expression node: {type(node).__name__}")
        if isinstance(node, ast.Call):
            if (
                not isinstance(node.func, ast.Name)
                or node.func.id not in _SAFE_FUNCTIONS
            ):
                raise ValueError(
                    f"Unsupported function: only {', '.join(_SAFE_FUNCTIONS)} allowed"
                )
            if node.keywords:
                raise ValueError("Keyword arguments not supported in expressions")
        if isinstance(node, ast.Attribute):
            if node.attr.startswith("_"):
                raise ValueError(
                    f"Access to private attribute {node.attr!r} not allowed"
                )
        if isinstance(node, ast.comprehension):
            if not isinstance(node.target, ast.Name):
                raise ValueError(
                    "Only simple variable names allowed in comprehension target"
                )
            if node.is_async:
                raise ValueError("Async comprehensions not supported")

def _safe_eval(node: ast.AST, values: dict[str, Any]) -> Any:
    if isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            return all(_safe_eval(v, values) for v in node.values)
        return any(_safe_eval(v, values) for v in node.values)

    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not _safe_eval(node.operand, values)

    if isinstance(node, ast.Compare):
        left = _safe_eval(node.left, values)
        for op, comparator in zip(node.ops, node.comparators):
            right = _safe_eval(comparator, values)
            op_func = _CMP_OPS.get(type(op))
            if op_func is None:
                raise ValueError(f"Unsupported compare op: {type(op).__name__}")
            if not op_func(left, right):
                return False
            left = right
        return True

    if isinstance(node, ast.Constant):
        return node.value

    if isinstance(node, ast.Name):
        if node.id not in values:
            raise ValueError(f"Unknown variable: {node.id}")
        return values[node.id]

    if isinstance(node, (ast.List, ast.Tuple)):
        return [_safe_eval(el, values) for el in node.elts]

    if isinstance(node, ast.Attribute):
        obj = _safe_eval(node.value, values)
        if not hasattr(obj, node.attr):
            raise ValueError(
                f"{type(obj).__name__!r} has no attribute {node.attr!r}"
            )
        return getattr(obj, node.attr)

    if isinstance(node, (ast.ListComp, ast.GeneratorExp)):
        return _eval_comprehension(node.generators, 0, node.elt, values)

    if isinstance(node, ast.Call):
        func_name = node.func.id
        args = [_safe_eval(a, values) for a in node.args]
        fn = any if func_name == "any" else all
        if len(args) == 1:
            return fn(args[0])
        if len(args) == 2:
            items, attr = args
            return fn(getattr(item, attr, False) for item in items)
        raise ValueError(f"{func_name}() takes 1 or 2 arguments, got {len(args)}")
        
    raise ValueError(f"Cannot evaluate node: {type(node).__name__}")

def _eval_comprehension(
    generators: list[ast.comprehension],
    gen_idx: int,
    elt: ast.AST,
    values: dict[str, Any],
) -> list:
    """递归求值推导式（支持多层 for 和 if 过滤）"""
    if gen_idx >= len(generators):
        return [_safe_eval(elt, values)]
    gen = generators[gen_idx]
    target_name = gen.target.id
    iterable = _safe_eval(gen.iter, values)
    results = []
    for item in iterable:
        inner = {**values, target_name: item}
        if all(_safe_eval(cond, inner) for cond in gen.ifs):
            results.extend(
                _eval_comprehension(generators, gen_idx + 1, elt, inner)
            )
    return results