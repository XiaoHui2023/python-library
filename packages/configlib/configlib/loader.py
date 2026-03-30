from __future__ import annotations

from pathlib import Path
from typing import Callable
from pydantic import BaseModel, ConfigDict, PrivateAttr

ReloadCallback = Callable[["ConfigLoader"], None]


class ConfigLoader(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    _file_path: Path = PrivateAttr()
    _on_update: ReloadCallback | None = PrivateAttr(default=None)
    _file_state: tuple[int, int] | None = PrivateAttr(default=None)

    def model_post_init(self, ctx) -> None:
        # 这里只保留空实现，避免实例化时立刻 reload
        pass

    @classmethod
    def from_file(
        cls,
        file_path: str | Path,
        on_update: ReloadCallback | None = None,
    ) -> "ConfigLoader":
        from . import load_config

        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"配置文件 {path} 不存在")

        data = load_config(str(path))
        if not isinstance(data, dict):
            raise TypeError(f"配置顶层必须是 dict，实际得到 {type(data).__name__}")

        obj = cls.model_validate(data)
        obj._file_path = path
        obj._on_update = on_update
        obj._file_state = obj._get_file_state()
        return obj

    def _get_file_state(self) -> tuple[int, int]:
        """获取文件状态"""
        stat = self._file_path.stat()
        return (stat.st_mtime_ns, stat.st_size)

    def has_changed(self) -> bool:
        """判断配置文件是否发生变化"""
        old_state = self._file_state
        new_state = self._get_file_state()
        self._file_state = new_state
        return old_state is None or old_state != new_state

    def reload(self) -> bool:
        """重新加载配置文件"""
        from . import load_config

        if not self.has_changed():
            return False

        data = load_config(str(self._file_path))
        if not isinstance(data, dict):
            raise TypeError(f"配置顶层必须是 dict，实际得到 {type(data).__name__}")

        new_obj = self.__class__.model_validate(data)

        for field_name in self.__class__.model_fields:
            setattr(self, field_name, getattr(new_obj, field_name))

        if self._on_update:
            self._on_update(self)

        return True