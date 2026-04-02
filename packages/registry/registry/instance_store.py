from __future__ import annotations

from difflib import get_close_matches
from typing import Iterator, TypeVar, Generic

T = TypeVar("T")


class InstanceStore(Generic[T]):
    def __init__(self) -> None:
        self._instances: dict[str, T] = {}

    def add(self, instance: T, name: str) -> T:
        """
        注册一个实例到注册表中。
        
        Args:
            instance: 实例。
            name: 实例名称。
            
        Returns:
            实例。
        """
        if name in self._instances:
            raise ValueError(f"重复实例 name={name!r}")

        self._instances[name] = instance
        return instance

    def exists(self, name: str) -> bool:
        return name in self._instances

    def get(self, name: str) -> T:
        if self.exists(name):
            return self._instances[name]

        suggested_name = self._suggest_name(name)
        if suggested_name:
            raise ValueError(f"未注册实例 {name!r}，是否在找 {suggested_name!r}")
        raise ValueError(f"未注册实例 {name!r}")

    def remove(self, name: str) -> T:
        if not self.exists(name):
            raise ValueError(f"未注册实例 {name!r}")
        return self._instances.pop(name)

    def clear(self) -> None:
        self._instances.clear()

    def items(self):
        return self._instances.items()

    def keys(self):
        return self._instances.keys()

    def values(self):
        return self._instances.values()

    def _suggest_name(self, name: str) -> str | None:
        matches = get_close_matches(name, self._instances.keys(), n=1, cutoff=0.6)
        return matches[0] if matches else None

    def __contains__(self, name: str) -> bool:
        return name in self._instances

    def __getitem__(self, name: str) -> T:
        return self.get(name)

    def __iter__(self) -> Iterator[T]:
        return iter(self._instances.values())

    def __len__(self) -> int:
        return len(self._instances)