from __future__ import annotations


class StateViewError(Exception):
    """字段读写或类型转换失败。"""

    def __init__(self, message: str, *, path: str = "") -> None:
        """
        Args:
            message: 错误说明
            path: 字段路径，如 cases.0.name
        """
        self.path = path
        if path:
            super().__init__(f"{path}: {message}")
        else:
            super().__init__(message)
