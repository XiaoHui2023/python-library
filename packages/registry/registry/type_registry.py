from __future__ import annotations
from typing import Callable, Iterator, TypeVar
from dataclasses import dataclass
from difflib import get_close_matches

T = TypeVar("T", bound=type)

@dataclass(frozen=True)
class TypeEntry:
    cls: type
    name: str

class TypeRegistry:
    def __init__(self) -> None:
        self._entries: list[TypeEntry] = []
        self._by_name: dict[str, TypeEntry] = {}

    def register(self, name: str) -> Callable[[T], T]:
        """
        注册一个类到注册表中。
        
        Args:
            name: 注册的名称。
            
        Returns:
            一个装饰器，用于将一个类注册到注册表中。
        """
        def decorator(cls: T) -> T:
            if name in self._by_name:
                raise ValueError(f"重复注册 name={name!r}")

            TypeEntry = TypeEntry(cls=cls, name=name)
            self._entries.append(TypeEntry)
            self._by_name[name] = TypeEntry
            return cls

        return decorator
        
    def __call__(self, name:str):
        return self.register(name=name)

    def namespace(self, field: str) -> Callable[..., Callable[[T], T]]:
        """
        将一个类注册到指定的命名空间中。
        
        Args:
            field: 命名空间字段名。
            
        Returns:
            一个装饰器，用于将一个类注册到指定的命名空间中。
        """
        def decorator(name: str) -> Callable[[T], T]:
            return self.register(name=f"{field}.{name}")
        return decorator

    def exists(self, name: str) -> bool:
        """
        检查名称是否已注册。
        
        Args:
            name: 注册的名称。
            
        Returns:
            True 如果名称已注册，否则返回 False。
        """
        return name in self._by_name

    def get(self, name: str) -> type:
        """
        根据名称获取已注册的类。
        
        Args:
            name: 注册的名称。
            
        Returns:
            已注册的类。
        """
        if self.exists(name):
            return self._by_name[name].cls
        else:
            suggested_name = self._suggest_name(name)
            if suggested_name:
                raise ValueError(f"未注册 {name!r}，是否在找 {suggested_name!r}")
            else:
                raise ValueError(f"未注册 {name!r}")

    def _suggest_name(self, name: str) -> str | None:
        """
        根据相似度，给出最接近的已注册名称。
        
        Args:
            name: 未注册的名称。
            
        Returns:
            最接近的已注册名称，如果找不到则返回 None。
        """
        matches = get_close_matches(name, self._by_name.keys(), n=1, cutoff=0.6)
        return matches[0] if matches else None

    def __iter__(self) -> Iterator[TypeEntry]:
        return iter(self._entries)

    def __contains__(self, name: str) -> bool:
        return name in self._by_name

    def __len__(self) -> int:
        return len(self._entries)

    def __getitem__(self, name: str) -> type:
        return self.get(name)

    def items(self) -> Iterator[tuple[str, type]]:
        """
        获取所有已注册的类。
        
        Returns:
            所有已注册的类。
        """
        for name, TypeEntry in self._by_name.items():
            yield name, TypeEntry.cls