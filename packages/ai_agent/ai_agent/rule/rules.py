from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path


class RuleSet:
    """
    会话级规则：由调用方指定文本文件路径，启动时读入并拼成系统提示。

    与 skill 不同，规则不注册工具，每轮运行固定注入模型上下文。
    """

    def __init__(self, paths: Sequence[Path | str] | None = None) -> None:
        self._segments: list[tuple[Path, str]] = []
        for raw in paths or ():
            path = Path(raw).expanduser().resolve()
            if not path.is_file():
                raise ValueError(f"rule 文件不存在或不是文件: {path}")
            text = path.read_text(encoding="utf-8").strip()
            self._segments.append((path, text))

    @property
    def paths(self) -> tuple[Path, ...]:
        """已加载的规则文件绝对路径。"""
        return tuple(path for path, _ in self._segments)

    def build_system_prompt(self) -> str:
        """
        将各规则文件正文按顺序拼接为系统提示。

        Returns:
            无规则或文件均为空时返回空字符串
        """
        parts = [text for _, text in self._segments if text]
        return "\n\n".join(parts)
