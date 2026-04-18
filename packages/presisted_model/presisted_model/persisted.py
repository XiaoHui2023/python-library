from __future__ import annotations

import atexit
import weakref
from pathlib import Path
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, PrivateAttr

from presisted_model.debounce import DebouncedAction
from presisted_model.storage import atomic_write_json

# BaseModel 实例不可哈希，不能用 WeakSet；用 id + weakref 在进程退出时刷盘。
_registry: dict[int, weakref.ReferenceType[PresistedModel]] = {}


class PresistedModel(BaseModel):
    """
    用 Pydantic 描述结构；子类通过 `load` 从文件恢复或新建，并在字段赋值后按防抖间隔落盘。
    仅跟踪「对模型字段的赋值」；对 list/dict 等原地修改不会触发保存。
    """

    model_config = ConfigDict(validate_assignment=True, arbitrary_types_allowed=True)

    _pm_path: Path | None = PrivateAttr(default=None)
    _pm_debounce: DebouncedAction | None = PrivateAttr(default=None)
    _pm_ready: bool = PrivateAttr(default=False)

    @classmethod
    def load(
        cls,
        path: str | Path,
        *,
        debounce_seconds: float = 0.5,
        json_indent: int | None = 2,
    ) -> Self:
        """
        从 `path` 读取 JSON 恢复实例；文件不存在则用默认字段构造。
        `debounce_seconds` 内多次修改只会在静止满该时间后写入最后一次状态。
        """
        path = Path(path)
        if path.exists():
            text = path.read_text(encoding="utf-8")
            obj = cls.model_validate_json(text)
        else:
            obj = cls()
        obj._pm_bootstrap(path, debounce_seconds, json_indent)
        return obj

    def _pm_bootstrap(
        self,
        path: Path,
        debounce_seconds: float,
        json_indent: int | None,
    ) -> None:
        self._pm_path = path.resolve()
        self._pm_debounce = DebouncedAction(
            lambda: self._pm_persist(json_indent),
            debounce_seconds,
        )
        self._pm_ready = True
        oid = id(self)

        def _drop(_wr: weakref.ReferenceType[PresistedModel]) -> None:
            _registry.pop(oid, None)

        _registry[oid] = weakref.ref(self, _drop)

    def __setattr__(self, name: str, value: Any) -> None:
        super().__setattr__(name, value)
        if not getattr(self, "_pm_ready", False):
            return
        if name.startswith("_"):
            return
        fields = getattr(self.__class__, "model_fields", None)
        if fields is None or name not in fields:
            return
        debouncer: DebouncedAction | None = getattr(self, "_pm_debounce", None)
        if debouncer is not None:
            debouncer.schedule()

    def _pm_persist(self, json_indent: int | None) -> None:
        p = getattr(self, "_pm_path", None)
        if p is None:
            return
        atomic_write_json(p, self, indent=json_indent)


def _pm_flush(model: PresistedModel) -> None:
    """仅本模块与进程退出时使用；不对外暴露。"""
    debouncer: DebouncedAction | None = getattr(model, "_pm_debounce", None)
    if debouncer is not None:
        debouncer.flush()


def _flush_all_registered() -> None:
    for r in list(_registry.values()):
        m = r()
        if m is not None:
            try:
                _pm_flush(m)
            except Exception:
                pass


atexit.register(_flush_all_registered)