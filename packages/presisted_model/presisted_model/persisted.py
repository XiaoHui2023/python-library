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

# 每个 resolve 后的路径至多一个活动实例；避免多实例防抖互相覆盖同一文件。
_paths_in_use: dict[Path, weakref.ReferenceType[PresistedModel]] = {}


def _claim_path(path: Path, owner: PresistedModel) -> None:
    key = path.resolve()
    wr = _paths_in_use.get(key)
    if wr is not None and wr() is not None:
        raise ValueError(
            f"PresistedModel already bound to {key}; only one live instance per file is allowed."
        )

    def _unlink(_dead: weakref.ReferenceType[PresistedModel]) -> None:
        _paths_in_use.pop(key, None)

    _paths_in_use[key] = weakref.ref(owner, _unlink)


class PresistedModel(BaseModel):
    """
    用 Pydantic 描述结构；子类通过 `load` 从文件恢复或新建，并在字段赋值后按防抖间隔落盘。
    首轮赋值启动固定间隔计时，该间隔内再次赋值不推迟计时，到时写入当前内存；写入后再赋值进入下一轮。
    仅跟踪「对模型字段的赋值」；对 list/dict 等原地修改不会触发保存。
    """

    model_config = ConfigDict(validate_assignment=True, arbitrary_types_allowed=True)

    _pm_path: Path | None = PrivateAttr(default=None)
    _pm_debounce: DebouncedAction | None = PrivateAttr(default=None)
    _pm_ready: bool = PrivateAttr(default=False)
    _pm_dirty: bool = PrivateAttr(default=False)
    _pm_last_disk_mtime_ns: int | None = PrivateAttr(default=None)
    _pm_existed_at_bootstrap: bool = PrivateAttr(default=False)

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
        首次字段赋值后启动 `debounce_seconds` 计时，该窗口内后续赋值不重置计时，
        计时结束时将当前状态写入；之后新的赋值再开始下一轮。
        同一 `path` 上同时只能有一个活动实例，否则抛出 `ValueError`。
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
        _claim_path(self._pm_path, self)
        existed = self._pm_path.exists()
        self._pm_existed_at_bootstrap = existed
        if existed:
            self._pm_last_disk_mtime_ns = self._pm_path.stat().st_mtime_ns
        else:
            self._pm_last_disk_mtime_ns = None
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
            object.__setattr__(self, "_pm_dirty", True)
            debouncer.schedule()

    def _pm_persist(self, json_indent: int | None) -> None:
        p = getattr(self, "_pm_path", None)
        if p is None:
            return
        atomic_write_json(p, self, indent=json_indent)
        object.__setattr__(self, "_pm_last_disk_mtime_ns", p.stat().st_mtime_ns)
        object.__setattr__(self, "_pm_dirty", False)


def _pm_flush(model: PresistedModel) -> None:
    """仅本模块与进程退出时使用；不对外暴露。"""
    if not getattr(model, "_pm_dirty", False):
        return
    p = getattr(model, "_pm_path", None)
    last_ns = getattr(model, "_pm_last_disk_mtime_ns", None)
    existed_at_boot = getattr(model, "_pm_existed_at_bootstrap", False)
    if p is not None and p.exists():
        disk_ns = p.stat().st_mtime_ns
        if last_ns is not None and disk_ns > last_ns:
            return
        if last_ns is None and not existed_at_boot:
            return
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