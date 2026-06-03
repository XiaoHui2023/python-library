from __future__ import annotations

from dataclasses import dataclass

from ai_agent.skill.catalog import SkillSummary


@dataclass(frozen=True)
class SkillToolDecl:
    """技能 frontmatter 中声明的一项子工具。"""

    name: str
    """注册到工具表时的短名（不含技能前缀）。"""
    handler: str
    """解析方式，仅允许内置引用形式。"""


@dataclass
class LoadedSkill:
    """已读取全文并完成 frontmatter 解析的技能。"""

    summary: SkillSummary
    """扫描摘要（根键、目录名、展示名与描述）。"""
    text: str
    """技能文件全文。"""
    meta: dict[str, str]
    """frontmatter 键值。"""
    body: str
    """正文 Markdown。"""
    tool_decls: tuple[SkillToolDecl, ...]
    """声明的子工具列表。"""
