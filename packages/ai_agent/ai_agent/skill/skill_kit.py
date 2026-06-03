from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from ai_agent.skill.manager import SkillManager
from ai_agent.tools import Tool


class SkillKit:
    """
    技能区入口：扫描、启用与工具导出委托底层管理器。

    技能仓库运行时只读；导出列表含管理工具与当前已启用子工具。

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

    def list_skills(self, root_key: str = "") -> str:
        """扫描 skill 根目录并列出摘要。"""
        return self._manager.list_skills(root_key)

    def get_metadata(self, skill_ref: str) -> str:
        """读取 frontmatter 元数据。"""
        return self._manager.get_metadata(skill_ref)

    def enable_skill(self, skill_ref: str) -> str:
        """启用 skill 及其子工具。"""
        return self._manager.enable_skill(skill_ref)

    def disable_skill(self, skill_ref: str) -> str:
        """停用 skill。"""
        return self._manager.disable_skill(skill_ref)

    def refresh(self) -> str:
        """重新扫描 skill 根。"""
        return self._manager.refresh()

    def roots_info(self) -> str:
        """说明 skill 根目录约束。"""
        return self._manager.roots_info()

    def build_management_tools(self) -> list[Tool]:
        """仅 skill 管理工具。"""
        return self._manager.build_management_tools()

    def build_enabled_tools(self) -> list[Tool]:
        """仅已启用 skill 的子工具。"""
        return self._manager.build_enabled_tools()

    def build_all_flat_tools(self) -> list[Tool]:
        """管理工具与已启用子工具。"""
        return self._manager.build_all_flat_tools()

    def build_tools(self) -> list[Tool]:
        """管理工具与已启用子工具（兼容旧用法）。"""
        return self.build_all_flat_tools()
