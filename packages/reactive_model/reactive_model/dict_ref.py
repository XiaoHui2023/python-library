from __future__ import annotations

from collections.abc import Iterable, Iterator, MutableMapping
from typing import Generic, TypeVar

from .ref import RefModel
from .track import track

K = TypeVar("K")
V = TypeVar("V")


class DictProxy(MutableMapping[K, V], Generic[K, V]):
    def __init__(self, owner: "DictRefModel[K, V]") -> None:
        self._owner = owner

    def __getitem__(self, key: K) -> V:
        return self._owner._value[key]

    def __setitem__(self, key: K, value: V) -> None:
        self._owner._value[key] = value
        self._owner.touch()

    def __delitem__(self, key: K) -> None:
        del self._owner._value[key]
        self._owner.touch()

    def __iter__(self) -> Iterator[K]:
        return iter(self._owner._value)

    def __len__(self) -> int:
        return len(self._owner._value)

    def clear(self) -> None:
        if self._owner._value:
            self._owner._value.clear()
            self._owner.touch()

    def update(self, other=(), /, **kwargs: V) -> None:
        changed = False

        if other:
            if hasattr(other, "items"):
                for k, v in other.items():
                    self._owner._value[k] = v
                    changed = True
            else:
                for k, v in other:
                    self._owner._value[k] = v
                    changed = True

        for k, v in kwargs.items():
            self._owner._value[k] = v
            changed = True

        if changed:
            self._owner.touch()

    def pop(self, key: K, default=...):
        if default is ...:
            value = self._owner._value.pop(key)
            self._owner.touch()
            return value

        if key in self._owner._value:
            value = self._owner._value.pop(key)
            self._owner.touch()
            return value
        return default

    def popitem(self) -> tuple[K, V]:
        item = self._owner._value.popitem()
        self._owner.touch()
        return item

    def setdefault(self, key: K, default: V = None):  # type: ignore[assignment]
        if key in self._owner._value:
            return self._owner._value[key]
        self._owner._value[key] = default
        self._owner.touch()
        return default

    def __repr__(self) -> str:
        return repr(self._owner._value)


class DictRefModel(RefModel[dict[K, V]]):
    def __init__(self, value: dict[K, V] | None = None) -> None:
        if value is None:
            value = {}
        super().__init__(value)
        self._proxy = DictProxy(self)

    @property
    def value(self) -> DictProxy[K, V]:
        track(self)
        return self._proxy

    @value.setter
    def value(self, value: dict[K, V]) -> None:
        self._value = value
        self.touch()