from __future__ import annotations

from difflib import get_close_matches
from typing import Callable, TypeVar

from pydantic import BaseModel, Field
from tree_model import TreeModel

T = TypeVar("T", bound=type)


class EntryNode(TreeModel):
    cls: type | None = Field(default=None, description="注册的类")


class Registry(BaseModel):
    def __init__(
        self,
        namespace: str = "",
        *,
        _root: EntryNode | None = None,
    ) -> None:
        self._namespace = namespace.strip(".")
        self._root = EntryNode(name="") if _root is None else _root

    def _full_name(self, name: str) -> str:
        if not self._namespace:
            return name
        return f"{self._namespace}.{name}"

    def _get_or_create_node(self, full_name: str) -> EntryNode:
        node = self._root
        for part in filter(None, full_name.split(".")):
            child = node.find_child(lambda item: item.name == part)
            if child is None:
                child = EntryNode(name=part)
                node.add_child(child)
            node = child
        return node

    def _find_node(self, full_name: str) -> EntryNode | None:
        node: EntryNode = self._root
        for part in filter(None, full_name.split(".")):
            found = node.find_child(lambda item: item.name == part)
            if found is None:
                return None
            node = found
        return node

    def _iter_registered_names(self) -> list[str]:
        names: list[str] = []

        def walk(node: EntryNode) -> None:
            if node.cls is not None and node.full_name:
                names.append(node.full_name)
            for child in node:
                walk(child)

        for child in self._root:
            walk(child)

        return names

    def _suggest_name(self, full_name: str) -> str | None:
        matches = get_close_matches(
            full_name,
            self._iter_registered_names(),
            n=1,
            cutoff=0.6,
        )
        return matches[0] if matches else None

    def register(self, name: str) -> Callable[[T], T]:
        """注册
        Args:
            name: 名称
        Returns:
            Callable[[T], T]: 装饰器
        """
        full_name = self._full_name(name)

        def decorator(cls: T) -> T:
            node = self._get_or_create_node(full_name)
            if node.cls is not None:
                raise ValueError(f"重复注册 name={full_name!r}")
            node.cls = cls
            return cls

        return decorator

    def __call__(self, name: str):
        return self.register(name=name)

    def namespace(self, full_name: str) -> "Registry":
        """命名空间
        Args:
            full_name: 全名
        Returns:
            Registry: 注册器
        """
        full_name = full_name.strip(".")
        if not full_name:
            return self
        namespace = f"{self._namespace}.{full_name}" if self._namespace else full_name
        return Registry(namespace=namespace, _root=self._root)

    def get(self, full_name: str) -> type:
        """获取注册的类
        Args:
            full_name: 全名
        Returns:
            type: 类
        """
        node = self._find_node(full_name)
        if node is None or node.cls is None:
            suggested_name = self._suggest_name(full_name)
            message = f"未找到 {full_name!r}"
            if suggested_name is not None:
                message += f"，是否想找 {suggested_name!r}"
            raise ValueError(message)
        return node.cls