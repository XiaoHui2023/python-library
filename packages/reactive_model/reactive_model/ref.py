from __future__ import annotations
from typing import TypeVar

from .reactive import ReactiveModel
from .track import track

T = TypeVar("T")


class RefModel(ReactiveModel[T]):
    def __init__(self, value: T) -> None:
        """
        Args:
            value: 值
        Attributes:
            _value: 值
        """
        super().__init__()
        self._value = value

    @property
    def value(self) -> T:
        track(self)
        return self._value

    @value.setter
    def value(self, value: T) -> None:
        self._value = value
        self.touch()