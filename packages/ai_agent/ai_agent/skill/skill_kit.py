from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from ai_agent.skill.manager import SkillManager
from ai_agent.tools import Tool


class SkillKit:
    """
    技能区入口：扫描、按需载入与工具导出委托底层管理器。

    技能仓库运行时只读；导出列表含管理工具与当前已载入 skill 的子工具。

    Args:
        roots: 技能根目录；可为单路径、路径序列或根键到路径的映射
        manager: 已构造的管理器；未传则按 roots 新建
    """

    def __init__(
        self,
        roots: Mapping[str, Path | str] | Sequence[Path | str] | Path | str,
        *,
        manager: SkillManager | None = None,
    ) -> None:
        if manager is None:
            self._manager = SkillManager(roots)
        else:
            self._manager = manager

    @property
    def manager(self) -> SkillManager:
        """底层动态能力管理器。"""
        return self._manager

    @property
    def root_keys(self) -> tuple[str, ...]:
        """已配置的根键名。"""
        return self._manager.root_keys

    def load_skill(self, skill_ref: str) -> str:
        """载入 skill 全文及其子工具。"""
        return self._manager.load_skill(skill_ref)

    def disable_skill(self, skill_ref: str) -> str:
        """卸载 skill。"""
        return self._manager.disable_skill(skill_ref)

    def refresh(self) -> str:
        """重新扫描 skill 根。"""
        return self._manager.refresh()

    def format_catalog_for_prompt(self) -> str:
        """生成须拼入系统提示的技能目录块。"""
        return self._manager.format_catalog_for_prompt()

    def build_management_tools(self) -> list[Tool]:
        """仅 skill 管理工具。"""
        return self._manager.build_management_tools()

    def build_enabled_tools(self) -> list[Tool]:
        """仅已载入 skill 的子工具。"""
        return self._manager.build_enabled_tools()

    def build_all_flat_tools(self) -> list[Tool]:
        """管理工具与已载入子工具。"""
        return self._manager.build_management_tools() + self._manager.build_enabled_tools()

    def build_tools(self) -> list[Tool]:
        """管理工具与已载入子工具（兼容旧用法）。"""
        return self.build_all_flat_tools()
