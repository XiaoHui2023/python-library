from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from .reactive_model import ReactiveModel
from .track import track

T = TypeVar("T")


class RefModel(ReactiveModel[T]):
    def __init__(self, value: T) -> None:
        """
        Args:
            value: 值
        Attributes:
            _value: 值
            _on_change_callbacks: value 赋值时调用的回调
        """
        super().__init__()
        self._value = value
        self._on_change_callbacks: list[Callable[[T, T], object]] = []

    @property
    def value(self) -> T:
        track(self)
        return self._value

    @value.setter
    def value(self, value: T) -> None:
        self._assign_value(value)

    def on_change(
        self, callback: Callable[[T, T], object]
    ) -> Callable[[T, T], object]:
        """注册在 value 被整体替换时执行的回调。

        Args:
            callback: 依次接收赋值后的新值、赋值前的旧值

        Returns:
            传入的 callback，便于作装饰器使用
        """
        self._on_change_callbacks.append(callback)
        return callback

    def _assign_value(self, value: T) -> None:
        old = self._value
        self._value = value
        self.touch()
        for callback in self._on_change_callbacks:
            callback(value, old)