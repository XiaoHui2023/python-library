from __future__ import annotations
from pydantic import BaseModel, Field, PrivateAttr
from typing import Optional, Callable, Iterator
from difflib import get_close_matches

class TreeModel(BaseModel):
    name: str = Field(..., description="节点名称")
    parent: Optional[TreeModel] = Field(None, description="父节点")
    _to_children: dict[str, TreeModel] = PrivateAttr(default_factory=dict)
    """子节点映射表"""
    _on_delete: list[Callable[[], None]] = PrivateAttr(default_factory=list)
    """删除回调"""
    _name_separator: str = PrivateAttr('.')
    """名称分隔符"""

    @property
    def full_name(self) -> str:
        """获取节点完整名称"""
        if self.parent is None:
            return self.name
        return f"{self.parent.full_name}{self._name_separator}{self.name}"

    def add_child(self, child: TreeModel):
        """添加子节点"""
        if child.parent is not None:
            raise ValueError(f"child {child.name!r} 已经有 parent")
        if child.name in self._to_children:
            raise ValueError(f"child {child.name!r} 已经是子节点")
        if self._name_separator in child.name:
            raise ValueError(f"child {child.name!r} 不允许包含名称分隔符")

        # 设置父节点
        child.parent = self

        # 添加子节点，并注册删除回调
        self._to_children[child.name] = child
        child.on_delete(lambda: self._to_children.pop(child.name))

    def delete(self) -> None:
        """删除节点"""
        # 删除子节点
        for child in list(self._to_children.values()):
            child.delete()
        self._to_children.clear()

        # 分离父节点
        self.parent = None

        # 执行删除回调
        for fn in self._on_delete:
            fn()
        self._on_delete.clear()

    def on_delete(self, callback: Callable[[], None]) -> Callable[[], None]:
        """注册删除回调"""
        self._on_delete.append(callback)
        return callback

    def _suggest_name(self, name: str) -> str | None:
        """
        根据相似度，给出最接近的已注册名称。
        
        Args:
            name: 未注册的名称。
            
        Returns:
            最接近的已注册名称，如果找不到则返回 None。
        """
        matches = get_close_matches(name, self._to_children.keys(), n=1, cutoff=0.6)
        return matches[0] if matches else None

    def exists_child(self, full_name: str, recursive: bool = False) -> bool:
        """
        检查子节点是否存在。
        
        Args:
            full_name: 完整名称。
            
        Returns:
            True 如果子节点存在，否则返回 False。
        """
        return self.find_child(full_name, recursive=recursive) is not None

    def get_child(self, full_name: str, recursive: bool = False) -> TreeModel:
        """获取子节点
        Args:
            full_name: 完整名称。
            
        Returns:
            节点。
        """
        child = self.find_child(full_name, recursive=recursive)
        if child is None:
            suggested_name = self._suggest_name(full_name)
            info = f"未找到 {full_name!r}"
            if suggested_name:
                info += f"，是否在找 {suggested_name!r}"
            raise ValueError(info)
        return child

    def find_child(self, full_name: str, recursive: bool = False) -> TreeModel|None:
        """查找子节点
        Args:
            full_name: 完整名称。
            
        Returns:
            节点。
        """
        if full_name in self._to_children:
            return self._to_children[full_name]

        if recursive:
            parts = self._relative_parts(full_name)
            if not parts:
                return None
            
            next_name = parts[0]
            if next_name not in self._to_children:
                return None
            
            next_level = self._to_children[next_name]
            next_full_name = self._name_separator.join(parts[1:])
            return next_level.find_child(next_full_name, recursive=recursive)

    def _relative_parts(self, full_name: str) -> list[str]:
        """
        将完整名称拆分为相对路径部分。
        
        Args:
            full_name: 完整名称。
            
        Returns:
            相对路径部分。
        """
        return full_name.split(self._name_separator)

    def __iter__(self) -> Iterator[TreeModel]:
        return iter(self._to_children.values())

    def __contains__(self, name: str) -> bool:
        return name in self._to_children

    def __len__(self) -> int:
        return len(self._to_children)

    def __getitem__(self, name: str) -> TreeModel:
        return self._to_children[name]

    def items(self) -> Iterator[tuple[str, TreeModel]]:
        return self._to_children.items()