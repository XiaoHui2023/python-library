from __future__ import annotations

from copy import deepcopy
from dataclasses import is_dataclass
from typing import Any

from .changelog import ChangeLog


def diff_values(
    old: Any,
    new: Any,
    path: str = "$",
    out: ChangeLog | None = None,
) -> ChangeLog:
    if out is None:
        out = ChangeLog()

    if type(old) is not type(new):
        out.type_changed(path, old, new)
        return out

    if isinstance(old, dict):
        old_keys = set(old)
        new_keys = set(new)

        for key in sorted(old_keys - new_keys, key=str):
            out.removed(_join_path(path, key), old[key])

        for key in sorted(new_keys - old_keys, key=str):
            out.added(_join_path(path, key), new[key])

        for key in sorted(old_keys & new_keys, key=str):
            diff_values(old[key], new[key], _join_path(path, key), out)

        return out

    if isinstance(old, (list, tuple)):
        common = min(len(old), len(new))

        for i in range(common):
            diff_values(old[i], new[i], f"{path}[{i}]", out)

        for i in range(common, len(old)):
            out.removed(f"{path}[{i}]", old[i])

        for i in range(common, len(new)):
            out.added(f"{path}[{i}]", new[i])

        return out

    if isinstance(old, (set, frozenset)):
        if old != new:
            out.updated(path, old, new)
        return out

    if old != new:
        out.updated(path, old, new)

    return out


def build_object(model_type: type[Any], data: Any) -> Any:
    payload = deepcopy(data)

    if model_type is dict:
        if not isinstance(payload, dict):
            raise TypeError("model_type=dict 时，配置顶层必须是 dict")
        return payload

    if model_type is list:
        if not isinstance(payload, list):
            raise TypeError("model_type=list 时，配置顶层必须是 list")
        return payload

    if model_type is set:
        if isinstance(payload, set):
            return payload
        if isinstance(payload, (list, tuple)):
            return set(payload)
        raise TypeError("model_type=set 时，配置顶层必须是 set/list/tuple")

    if _is_pydantic_model_class(model_type):
        return model_type.model_validate(payload)

    if is_dataclass(model_type):
        if not isinstance(payload, dict):
            raise TypeError("dataclass 类型要求配置顶层为 dict")
        return model_type(**payload)

    if isinstance(payload, dict):
        return model_type(**payload)

    return model_type(payload)


def _join_path(base: str, key: Any) -> str:
    if isinstance(key, int):
        return f"{base}[{key}]"
    key_text = str(key)
    if key_text.isidentifier():
        return f"{base}.{key_text}"
    return f"{base}[{key_text!r}]"


def _is_pydantic_model_class(tp: Any) -> bool:
    return hasattr(tp, "model_validate") and hasattr(tp, "model_fields")