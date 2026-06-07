from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ai_agent.skill.frontmatter import split_frontmatter
from ai_agent.skill.roots import SkillRootsSandbox

_MAX_READ_BYTES = 512 * 1024
_SKILL_FILE = "SKILL.md"


@dataclass(frozen=True)
class SkillSummary:
    """扫描得到的技能摘要（不含正文）。"""

    root_key: str
    """配置的技能根键名。"""
    skill_id: str
    """根目录下技能子文件夹名。"""
    name: str
    """frontmatter 中的展示名。"""
    description: str
    """frontmatter 中的简短说明。"""

    @property
    def skill_ref(self) -> str:
        return f"{self.root_key}/{self.skill_id}"


def scan_skills(sandbox: SkillRootsSandbox) -> list[SkillSummary]:
    """
    扫描所有根目录下含 SKILL.md 的子目录。

    Args:
        sandbox: 已配置的 skill 根

    Returns:
        按 skill_ref 字典序排列的摘要列表
    """
    found: list[SkillSummary] = []
    for root_key in sandbox.root_keys:
        root = sandbox.root_path(root_key)
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir()):
            if not child.is_dir():
                continue
            skill_md = child / _SKILL_FILE
            if not skill_md.is_file():
                continue
            summary = _summary_from_file(root_key, child.name, skill_md)
            found.append(summary)
    found.sort(key=lambda item: item.skill_ref)
    return found


def load_skill_text(sandbox: SkillRootsSandbox, skill_ref: str) -> str:
    """
    读取 SKILL.md 全文。

    Args:
        sandbox: skill 根沙箱
        skill_ref: ``{root_key}/{skill_id}``

    Returns:
        文件全文
    """
    path = sandbox.skill_md_path(skill_ref)
    if not path.is_file():
        raise ValueError(f"未找到 SKILL.md: {skill_ref}")
    return _read_bounded(path)


def format_skill_list(summaries: list[SkillSummary]) -> str:
    """将摘要列表格式化为模型可读文本（不含宿主机绝对路径）。"""
    if not summaries:
        return "（未找到 skill）"
    lines: list[str] = []
    for item in summaries:
        lines.append(
            f"- {item.skill_ref} | name={item.name} | {item.description}"
        )
    return "\n".join(lines)


def format_skill_catalog_prompt(summaries: list[SkillSummary]) -> str:
    """拼入系统提示的技能目录块（仅 name 与 description）。"""
    listing = format_skill_list(summaries)
    if listing == "（未找到 skill）":
        return ""
    return (
        "## 可用技能\n\n"
        "下列为技能目录（仅 name 与 description）。"
        "需要按某技能执行时，调用 **skill__load_skill** 载入该技能全文；"
        "每轮对同一技能只需载入一次。\n\n"
        f"{listing}"
    )


def _summary_from_file(root_key: str, skill_id: str, skill_md: Path) -> SkillSummary:
    raw = _read_bounded(skill_md)
    meta, _ = split_frontmatter(raw)
    name = meta.get("name", "").strip() or skill_id
    description = meta.get("description", "").strip()
    return SkillSummary(
        root_key=root_key,
        skill_id=skill_id,
        name=name,
        description=description,
    )


def _read_bounded(path: Path) -> str:
    size = path.stat().st_size
    if size > _MAX_READ_BYTES:
        raise ValueError(f"文件过大（>{_MAX_READ_BYTES} 字节）")
    return path.read_text(encoding="utf-8", errors="replace")
