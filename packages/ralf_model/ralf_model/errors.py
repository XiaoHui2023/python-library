from __future__ import annotations

from pathlib import Path


class RalfError(Exception):
    """RALF 解析或生成错误基类。"""


class RalfParseError(RalfError):
    """文本不符合预期语法或词法。"""

    def __init__(self, message: str, *, line: int, col: int) -> None:
        super().__init__(f"{message} (行 {line}, 列 {col})")
        self.line = line
        self.col = col


class RalfSourceError(RalfError):
    """source 展开或路径解析失败（含循环引用、找不到文件）。"""

    def __init__(self, message: str, *, path: Path | None = None) -> None:
        super().__init__(message)
        self.path = path
