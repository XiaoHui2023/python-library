from __future__ import annotations
from pydantic import BaseModel, Field, PrivateAttr
from typing import Optional, Callable

class TreeNode(BaseModel):
    name: str = Field(..., description="节点名称")
    parent: Optional[TreeNode] = Field(None, description="父节点")
    children: list[TreeNode] = Field(default_factory=list, description="子节点")
    _on_delete: list[Callable[[], None]] = PrivateAttr(default_factory=list, description="删除回调")

    @property
    def full_name(self) -> str:
        """获取节点完整名称"""
        if self.parent is None:
            return self.name
        return f"{self.parent.full_name}.{self.name}"

    def add_child(self, child: TreeNode):
        """添加子节点"""
        if child.parent is not None:
            raise ValueError("child 已经有 parent")
        if child in self.children:
            raise ValueError("child 已经是子节点")

        # 设置父节点
        child.parent = self

        # 添加子节点，并注册删除回调
        self.children.append(child)
        child.on_delete(lambda: self.children.remove(child))

    def delete(self) -> None:
        """删除节点"""
        # 删除子节点
        for child in list(self.children):
            child.delete()
        self.children.clear()

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