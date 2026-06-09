from __future__ import annotations

from typing import Any, Callable

from .convert import from_data
from .errors import StateViewError
from .fields import FieldSpec


def apply_patch(
    obj: Any,
    patch: dict[str, Any],
    specs: list[FieldSpec],
    *,
    is_editable: Callable[[str, FieldSpec], bool],
) -> None:
    """按字段规则把 patch 写入实例。"""
    if not isinstance(patch, dict):
        raise StateViewError("patch 需要对象")

    spec_map = {spec.name: spec for spec in specs}
    for key in patch:
        if key not in spec_map:
            raise StateViewError(f"未知字段 {key!r}", path=key)
        spec = spec_map[key]
        if not is_editable(key, spec):
            raise StateViewError(f"字段 {key!r} 不可编辑", path=key)

    for key, raw_value in patch.items():
        spec = spec_map[key]
        value = from_data(raw_value, spec.type_hint, path=key)
        setattr(obj, key, value)
