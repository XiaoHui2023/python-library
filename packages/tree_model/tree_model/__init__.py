from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Optional

from pydantic import BaseModel, Field, PrivateAttr
from reactive_model import ListRefModel


class TreeModel(BaseModel):
    name: str = Field(..., description="节点名称")
    parent: Optional["TreeModel"] = Field(None, description="父节点")

    _children: ListRefModel["TreeModel"] = PrivateAttr(default_factory=ListRefModel)
    _on_delete: list[Callable[[], None]] = PrivateAttr(default_factory=list)
    _name_separator: str = PrivateAttr(".")

    @property
    def full_name(self) -> str:
        if self.parent is None:
            return self.name
        return f"{self.parent.full_name}{self._name_separator}{self.name}"

    def add_child(self, child: "TreeModel") -> None:
        if child.parent is not None:
            raise ValueError(f"child {child.name!r} 已经有 parent")
        if self._name_separator in child.name:
            raise ValueError(f"child {child.name!r} 不允许包含名称分隔符")
        if any(item is child for item in self._children.value):
            raise ValueError("child 已经是子节点")

        child.parent = self
        self._children.value.append(child)
        child.on_delete(lambda: self._remove_child(child))

    def _remove_child(self, child: "TreeModel") -> None:
        children = self._children.value
        for index, item in enumerate(children):
            if item is child:
                del children[index]
                break

    def delete(self) -> None:
        for child in list(self._children.value):
            child.delete()

        self._children.value.clear()
        self.parent = None

        for fn in self._on_delete:
            fn()
        self._on_delete.clear()

    def on_delete(self, callback: Callable[[], None]) -> Callable[[], None]:
        self._on_delete.append(callback)
        return callback

    def find_child(
        self,
        predicate: Callable[["TreeModel"], bool],
        recursive: bool = False,
    ) -> "TreeModel | None":
        for child in self._children.value:
            if predicate(child):
                return child
            if recursive:
                found = child.find_child(predicate, recursive=True)
                if found is not None:
                    return found
        return None

    def filter_child(
        self,
        predicate: Callable[["TreeModel"], bool],
        recursive: bool = False,
    ) -> list["TreeModel"]:
        result: list[TreeModel] = []
        for child in self._children.value:
            if predicate(child):
                result.append(child)
            if recursive:
                result.extend(child.filter_child(predicate, recursive=True))
        return result

    def exists_child(
        self,
        predicate: Callable[["TreeModel"], bool],
        recursive: bool = False,
    ) -> bool:
        return self.find_child(predicate, recursive=recursive) is not None

    def get_child(
        self,
        predicate: Callable[["TreeModel"], bool],
        recursive: bool = False,
    ) -> "TreeModel":
        child = self.find_child(predicate, recursive=recursive)
        if child is None:
            raise ValueError("未找到符合条件的子节点")
        return child

    def find_child_by_name(self, name: str, recursive: bool = False) -> "TreeModel | None":
        return self.find_child(lambda node: node.name == name, recursive=recursive)

    def __iter__(self) -> Iterator["TreeModel"]:
        return iter(self._children.value)

    def __len__(self) -> int:
        return len(self._children.value)