from __future__ import annotations

from dataclasses import MISSING, fields, is_dataclass
from enum import Enum
from typing import Any, get_args, get_origin

from .errors import StateViewError


def resolve_type_hint(type_hint: Any) -> Any:
    if type_hint is None:
        return None
    origin = get_origin(type_hint)
    if origin is None:
        return type_hint
    args = get_args(type_hint)
    if origin in (list, tuple, dict):
        return type_hint
    non_none = [item for item in args if item is not type(None)]
    if len(non_none) == 1:
        return resolve_type_hint(non_none[0])
    return type_hint


def is_enum_type(type_hint: Any) -> bool:
    hint = resolve_type_hint(type_hint)
    return isinstance(hint, type) and issubclass(hint, Enum)


def is_dataclass_type(type_hint: Any) -> bool:
    hint = resolve_type_hint(type_hint)
    return isinstance(hint, type) and is_dataclass(hint)


def to_data(value: Any, *, path: str = "") -> Any:
    if value is None:
        return None
    if isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        result: dict[str, Any] = {}
        for field in fields(value):
            field_path = f"{path}.{field.name}" if path else field.name
            result[field.name] = to_data(getattr(value, field.name), path=field_path)
        return result
    if isinstance(value, dict):
        return {
            str(key): to_data(item, path=f"{path}.{key}" if path else str(key))
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [
            to_data(item, path=f"{path}.{index}" if path else str(index))
            for index, item in enumerate(value)
        ]
    raise StateViewError(
        f"不支持的类型 {type(value).__name__}",
        path=path,
    )


def _parse_enum(enum_type: type[Enum], value: Any, *, path: str) -> Enum:
    if isinstance(value, enum_type):
        return value
    if isinstance(value, str):
        try:
            return enum_type(value)
        except ValueError:
            pass
        try:
            return enum_type[value]
        except KeyError:
            pass
    options = [member.value for member in enum_type]
    raise StateViewError(
        f"无效的枚举值 {value!r}，可选 {options}",
        path=path,
    )


def from_data(value: Any, type_hint: Any, *, path: str = "") -> Any:
    hint = resolve_type_hint(type_hint)
    if value is None:
        return None
    if hint is None or hint is Any:
        return value
    if is_enum_type(hint):
        return _parse_enum(hint, value, path=path)
    if is_dataclass_type(hint):
        if not isinstance(value, dict):
            raise StateViewError("需要对象", path=path)
        return _dict_to_dataclass(hint, value, path=path)
    origin = get_origin(hint)
    if origin in (list, tuple):
        if not isinstance(value, list):
            raise StateViewError("需要数组", path=path)
        item_hint = get_args(hint)[0] if get_args(hint) else Any
        return [
            from_data(item, item_hint, path=f"{path}.{index}" if path else str(index))
            for index, item in enumerate(value)
        ]
    if origin is dict:
        if not isinstance(value, dict):
            raise StateViewError("需要对象", path=path)
        key_hint, value_hint = get_args(hint) if get_args(hint) else (Any, Any)
        return {
            from_data(key, key_hint, path=f"{path}.{key}" if path else str(key)): from_data(
                item,
                value_hint,
                path=f"{path}.{key}" if path else str(key),
            )
            for key, item in value.items()
        }
    if hint is bool:
        if not isinstance(value, bool):
            raise StateViewError("需要布尔值", path=path)
        return value
    if hint is int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise StateViewError("需要整数", path=path)
        return value
    if hint is float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise StateViewError("需要数字", path=path)
        return float(value)
    if hint is str:
        if not isinstance(value, str):
            raise StateViewError("需要字符串", path=path)
        return value
    if isinstance(hint, type) and isinstance(value, hint):
        return value
    raise StateViewError(
        f"无法把 {type(value).__name__} 转为 {getattr(hint, '__name__', hint)}",
        path=path,
    )


def _dict_to_dataclass(cls: type[Any], data: dict[str, Any], *, path: str) -> Any:
    field_map = {field.name: field for field in fields(cls)}
    missing_keys = [name for name in data if name not in field_map]
    if missing_keys:
        raise StateViewError(f"未知字段 {missing_keys[0]!r}", path=path)

    kwargs: dict[str, Any] = {}
    for name, field in field_map.items():
        if name not in data:
            if field.default is not MISSING:
                continue
            if field.default_factory is not MISSING:
                continue
            raise StateViewError(f"缺少必填字段 {name!r}", path=path)
        field_path = f"{path}.{name}" if path else name
        kwargs[name] = from_data(data[name], field.type, path=field_path)
    return cls(**kwargs)
