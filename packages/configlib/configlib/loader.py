from __future__ import annotations
import inspect
from pathlib import Path
from typing import Callable
from pydantic import BaseModel, ConfigDict, PrivateAttr
from typing import TypeVar
T = TypeVar("T", bound="ConfigLoader")

ReloadCallback = Callable[..., None]


class ConfigLoader(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    _file_path: Path | None = PrivateAttr(default=None)
    _on_update: ReloadCallback | None = PrivateAttr(default=None)
    _file_state: tuple[int, int] | None = PrivateAttr(default=None)

    @classmethod
    def from_file(
        cls: type[T],
        file_path: str | Path,
        on_update: ReloadCallback | None = None,
    ) -> T:
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"配置文件 {path} 不存在")

        data = cls._load_dict(path)

        obj = cls.model_validate(data)
        obj._file_path = path
        obj._on_update = on_update
        obj._file_state = obj._get_file_state()
        return obj

    @staticmethod
    def _load_dict(path: Path) -> dict:
        from . import load_config
        data = load_config(str(path))
        if not isinstance(data, dict):
            raise TypeError(f"配置顶层必须是 dict，实际得到 {type(data).__name__}")
        return data

    def _get_file_state(self) -> tuple[int, int]:
        """获取文件状态"""
        if self._file_path is None:
            raise RuntimeError("此实例未绑定配置文件，请使用 from_file() 创建")
        stat = self._file_path.stat()
        return (stat.st_mtime_ns, stat.st_size)

    def has_changed(self) -> bool:
        """判断配置文件是否发生变化（纯查询，不更新内部状态）"""
        if self._file_path is None:
            return False
        return self._file_state is None or self._file_state != self._get_file_state()

    def reload(self) -> bool:
        """重新加载配置文件"""
        if not self.has_changed():
            return False

        data = self._load_dict(self._file_path)

        old = self.model_copy(deep=True)
        new_obj = self.__class__.model_validate(data)

        for field_name in self.__class__.model_fields:
            setattr(self, field_name, getattr(new_obj, field_name))

        self._file_state = self._get_file_state()
        self._call_update_callback(old)

        return True

    def _call_update_callback(self, old: "ConfigLoader") -> None:
        """调用更新回调函数"""
        if self._on_update is None:
            return
        callback = self._on_update
        try:
            sig = inspect.signature(callback)
        except (ValueError, TypeError):
            for args in [(self, old), (self,), ()]:
                try:
                    callback(*args)
                    return
                except TypeError:
                    continue
            raise TypeError(f"无法调用回调函数 {callback!r}，请检查其参数签名")

        params = [
            p for p in sig.parameters.values()
            if p.default is inspect.Parameter.empty
            and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        ]
        if len(params) >= 2:
            callback(self, old)
        elif len(params) == 1:
            callback(self)
        else:
            callback()

__all__ = ["ConfigLoader"]