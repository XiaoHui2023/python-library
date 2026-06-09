from __future__ import annotations

from dataclasses import dataclass
from dataclasses import fields as dataclass_fields
from dataclasses import is_dataclass
from typing import Any, Literal, get_args, get_origin

from .convert import is_dataclass_type, is_enum_type, resolve_type_hint, to_data


FieldKind = Literal["field", "property"]


@dataclass(frozen=True)
class FieldSpec:
    """单个导出字段的元数据。"""

    name: str
    kind: FieldKind
    type_hint: Any


def _property_return_type(prop: property) -> Any:
    func = prop.fget
    if func is None:
        return Any
    return func.__annotations__.get("return", Any)


def collect_fields(obj: Any) -> list[FieldSpec]:
    """扫描实例上的数据字段与 property。"""
    cls = type(obj)
    specs: list[FieldSpec] = []
    seen: set[str] = set()

    if is_dataclass(cls):
        for field in dataclass_fields(cls):
            specs.append(FieldSpec(field.name, "field", field.type))
            seen.add(field.name)
    elif hasattr(cls, "__annotations__"):
        for name, hint in cls.__annotations__.items():
            if name.startswith("_"):
                continue
            specs.append(FieldSpec(name, "field", hint))
            seen.add(name)

    for name, member in cls.__dict__.items():
        if name.startswith("_"):
            continue
        if not isinstance(member, property):
            continue
        specs.append(FieldSpec(name, "property", _property_return_type(member)))

    return specs


def schema_type_name(type_hint: Any) -> str:
    hint = resolve_type_hint(type_hint)
    if is_enum_type(hint):
        return "enum"
    if is_dataclass_type(hint):
        return "object"
    origin = get_origin(hint)
    if origin in (list, tuple):
        return "array"
    if origin is dict:
        return "object"
    if hint is bool:
        return "boolean"
    if hint is int:
        return "integer"
    if hint is float:
        return "number"
    if hint is str:
        return "string"
    return "string"


def build_field_schema(spec: FieldSpec, *, editable: bool) -> dict[str, Any]:
    """生成单个字段的 schema 条目。"""
    entry: dict[str, Any] = {
        "type": schema_type_name(spec.type_hint),
    }
    if spec.kind == "property":
        entry["readonly"] = True
        entry["computed"] = True
        entry["editable"] = False
    else:
        entry["editable"] = editable
        if not editable:
            entry["readonly"] = True

    hint = resolve_type_hint(spec.type_hint)
    if is_enum_type(hint):
        entry["enum"] = [member.value for member in hint]
    elif schema_type_name(spec.type_hint) == "array":
        args = get_args(spec.type_hint)
        item_hint = args[0] if args else Any
        entry["items"] = _nested_schema(item_hint, editable=editable)
    elif is_dataclass_type(hint):
        entry["properties"] = {
            field.name: build_field_schema(
                FieldSpec(field.name, "field", field.type),
                editable=editable,
            )
            for field in dataclass_fields(hint)
        }
    return entry


def _nested_schema(type_hint: Any, *, editable: bool) -> dict[str, Any]:
    hint = resolve_type_hint(type_hint)
    entry: dict[str, Any] = {"type": schema_type_name(type_hint)}
    if is_enum_type(hint):
        entry["enum"] = [member.value for member in hint]
    elif is_dataclass_type(hint):
        entry["type"] = "object"
        entry["properties"] = {
            field.name: build_field_schema(
                FieldSpec(field.name, "field", field.type),
                editable=editable,
            )
            for field in dataclass_fields(hint)
        }
    return entry


def read_field_value(obj: Any, spec: FieldSpec) -> Any:
    return getattr(obj, spec.name)


def export_data(obj: Any, specs: list[FieldSpec]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for spec in specs:
        value = read_field_value(obj, spec)
        data[spec.name] = to_data(value, path=spec.name)
    return data
