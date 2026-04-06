from __future__ import annotations

from difflib import get_close_matches
from typing import Any

from pydantic import BaseModel, Field
from tree_model import TreeModel


class EntryNode(TreeModel):
    obj: Any | None = Field(default=None, description="注册对象")


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
            if node.obj is not None and node.full_name:
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

    def register(self, name: str, obj: Any) -> Any:
        """注册对象"""
        full_name = self._full_name(name)

        node = self._get_or_create_node(full_name)
        if node.obj is not None:
            raise ValueError(f"重复注册 {full_name!r}")
        node.obj = obj
        return obj

    def __call__(self, name: str, obj: Any | None = None) -> Any:
        if obj is not None:
            return self.register(name=name, obj=obj)
        def decorator(target: Any) -> Any:
            return self.register(name=name, obj=target)
        return decorator

    def namespace(self, full_name: str) -> "Registry":
        """命名空间"""
        full_name = full_name.strip(".")
        if not full_name:
            return self
        namespace = f"{self._namespace}.{full_name}" if self._namespace else full_name
        return Registry(namespace=namespace, _root=self._root)

    def get(self, name: str) -> Any:
        """获取注册对象"""
        full_name = self._full_name(name)
        node = self._find_node(full_name)
        if node is None or node.obj is None:
            suggested_name = self._suggest_name(full_name)
            message = f"未找到 {full_name!r}"
            if suggested_name is not None:
                message += f"，是否想找 {suggested_name!r}"
            raise ValueError(message)
        return node.obj