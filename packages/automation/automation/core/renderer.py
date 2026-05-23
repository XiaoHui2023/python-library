from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from express_evaluator import Evaluator


class Renderer:
    """绑定一份变量表，用 express_evaluator 做表达式与占位符求值。"""

    def __init__(self, data: dict[str, Any]) -> None:
        """用于求值的变量表。

        Args:
            data: 与表达式对应的键值；根表通常内含实体、事件、触发器与上下文引用
        """
        self._data = data
        self._evaluator = Evaluator()

    @property
    def data(self) -> dict[str, Any]:
        """当前变量表的浅拷贝；顶层键与运行时里的实体等对象共享引用。"""

        return dict(self._data)

    def derive(self, overlay: Mapping[str, Any]) -> Renderer:
        """叠一层变量后返回新渲染器。

        Args:
            overlay: 要并入的键值，同名键以这里为准

        Returns:
            使用合并后新 dict 的渲染器
        """
        return Renderer({**self.data, **dict(overlay)})

    def __call__(self, expression: str) -> Any:
        """对表达式求值（含花括号占位符时由库内替换再算）。"""
        return self._evaluator(expression, self.data)
