from __future__ import annotations
from typing import Generic, TypeVar

T = TypeVar("T")


class ReactiveModel(Generic[T]):
    def __init__(self) -> None:
        """
        Attributes:
            _version: 版本号
        """
        self._version = 0

    @property
    def version(self) -> int:
        """版本号"""
        return self._version

    def touch(self) -> None:
        """标记为改动"""
        self._version += 1

    @property
    def value(self) -> T:
        """值"""
        raise NotImplementedError