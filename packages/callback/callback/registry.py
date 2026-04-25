from __future__ import annotations

from collections.abc import Callable
from typing import Any


class LayerTier:
    """单层登记：收集可调用对象；与哪类根、同步或异步 trigger 一起用，由子类在登记时按约定约束。"""

    def __init__(self, bucket: list[Callable[..., Any]]) -> None:
        self._list = bucket

    def register(self, func: Callable[..., Any]) -> None:
        """登记一个处理函数，同一对象只保留一条。"""
        if func not in self._list:
            self._list.append(func)

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """装饰器用法：登记后仍返回原可调用对象。"""
        self.register(func)
        return func


class CallbackLayers:
    """分层登记：前、中、后三段各持有一份已登记的处理函数列表。"""

    def __init__(self) -> None:
        self._before: list[Callable[..., Any]] = []
        self._middle: list[Callable[..., Any]] = []
        self._after: list[Callable[..., Any]] = []
        self.before = LayerTier(self._before)
        self.middle = LayerTier(self._middle)
        self.after = LayerTier(self._after)

    def tier_lists_in_order(self) -> list[list[Callable[..., Any]]]:
        """按触发顺序返回三层列表；层内顺序与登记顺序一致。"""
        return [self._before, self._middle, self._after]

    def clear(self) -> None:
        """清空三段上的全部已登记处理函数。"""
        self._before.clear()
        self._middle.clear()
        self._after.clear()


__all__ = ["CallbackLayers", "LayerTier"]
