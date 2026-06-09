from __future__ import annotations

from typing import Any

from .errors import StateViewError
from .fields import FieldSpec, build_field_schema, collect_fields, export_data
from .patch import apply_patch


class StateView:
    """把 Python 数据实例投影为前端可读写 data 与 schema。"""

    def __init__(
        self,
        obj: Any,
        *,
        editable: list[str] | None = None,
        readonly: list[str] | None = None,
    ) -> None:
        """
        Args:
            obj: 被包装的 Python 数据实例
            editable: 允许前端修改的字段名；给出后仅列出的字段可写
            readonly: 禁止前端修改的字段名
        """
        if obj is None:
            raise StateViewError("obj 不能为空")
        self._obj = obj
        self._editable = set(editable) if editable is not None else None
        self._readonly = set(readonly) if readonly is not None else set()
        self._specs = collect_fields(obj)
        known = {spec.name for spec in self._specs}
        for name in self._readonly:
            if name not in known:
                raise StateViewError(f"readonly 含未知字段 {name!r}")
        if self._editable is not None:
            for name in self._editable:
                if name not in known:
                    raise StateViewError(f"editable 含未知字段 {name!r}")

    @property
    def obj(self) -> Any:
        """被包装的原始实例。"""
        return self._obj

    def get(self) -> dict[str, Any]:
        """返回当前完整数据，含 property 计算值。"""
        return export_data(self._obj, self._specs)

    def set(self, patch: dict[str, Any]) -> dict[str, Any]:
        """
        Args:
            patch: 前端提交的字段修改；顶层按 key 合并，list 与嵌套对象整段替换

        Returns:
            写入后的完整数据
        """
        apply_patch(
            self._obj,
            patch,
            self._specs,
            is_editable=self._field_editable,
        )
        return self.get()

    def schema(self) -> dict[str, dict[str, Any]]:
        """返回各字段的类型与可编辑说明。"""
        return {
            spec.name: build_field_schema(spec, editable=self._field_editable(spec.name, spec))
            for spec in self._specs
        }

    def _field_editable(self, name: str, spec: FieldSpec) -> bool:
        if spec.kind == "property":
            return False
        if name in self._readonly:
            return False
        if self._editable is not None:
            return name in self._editable
        return True
