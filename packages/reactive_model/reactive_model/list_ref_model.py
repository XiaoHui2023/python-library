from __future__ import annotations

from collections.abc import Iterable, MutableSequence
from typing import Generic, TypeVar, overload

from .ref_model import RefModel
from .track import track

T = TypeVar("T")


class ListProxy(MutableSequence[T], Generic[T]):
    def __init__(self, owner: "ListRefModel[T]") -> None:
        self._owner = owner

    def __len__(self) -> int:
        return len(self._owner._value)

    @overload
    def __getitem__(self, index: int) -> T: ...

    @overload
    def __getitem__(self, index: slice) -> list[T]: ...

    def __getitem__(self, index: int | slice) -> T | list[T]:
        return self._owner._value[index]

    @overload
    def __setitem__(self, index: int, value: T) -> None: ...

    @overload
    def __setitem__(self, index: slice, value: Iterable[T]) -> None: ...

    def __setitem__(self, index: int | slice, value: T | Iterable[T]) -> None:
        self._owner._value[index] = value  # type: ignore[index,assignment]
        self._owner.touch()

    def __delitem__(self, index: int | slice) -> None:
        del self._owner._value[index]
        self._owner.touch()

    def insert(self, index: int, value: T) -> None:
        self._owner._value.insert(index, value)
        self._owner.touch()

    def append(self, value: T) -> None:
        self._owner._value.append(value)
        self._owner.touch()

    def extend(self, values: Iterable[T]) -> None:
        self._owner._value.extend(values)
        self._owner.touch()

    def clear(self) -> None:
        if self._owner._value:
            self._owner._value.clear()
            self._owner.touch()

    def pop(self, index: int = -1) -> T:
        item = self._owner._value.pop(index)
        self._owner.touch()
        return item

    def remove(self, value: T) -> None:
        self._owner._value.remove(value)
        self._owner.touch()

    def reverse(self) -> None:
        self._owner._value.reverse()
        self._owner.touch()

    def sort(self, *args: object, **kwargs: object) -> None:
        self._owner._value.sort(*args, **kwargs)  # type: ignore[arg-type]
        self._owner.touch()

    def __iadd__(self, other: Iterable[T]) -> ListProxy[T]:
        self._owner._value += list(other)
        self._owner.touch()
        return self

    def __repr__(self) -> str:
        return repr(self._owner._value)


class ListRefModel(RefModel[list[T]]):
    def __init__(self, value: list[T] | None = None) -> None:
        if value is None:
            value = []
        super().__init__(value)
        self._proxy = ListProxy(self)

    @property
    def value(self) -> ListProxy[T]:
        track(self)
        return self._proxy

    @value.setter
    def value(self, value: list[T]) -> None:
        self._assign_value(value)
