from __future__ import annotations

import re

from ai_agent.skill.models import SkillToolDecl

_FRONTMATTER_RE = re.compile(
    r"\A---\r?\n(.*?)\r?\n---\r?\n?",
    re.DOTALL,
)


def parse_tool_declarations(text: str) -> list[SkillToolDecl]:
    """
    从 SKILL.md 全文解析 frontmatter 中的 tools 列表。

    Args:
        text: SKILL.md 全文

    Returns:
        声明列表；无 tools 段时为空
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return []
    return _parse_tools_block(match.group(1))


def _parse_tools_block(frontmatter: str) -> list[SkillToolDecl]:
    lines = frontmatter.splitlines()
    start = -1
    for index, line in enumerate(lines):
        if line.strip() == "tools:":
            start = index + 1
            break
    if start < 0:
        return []
    decls: list[SkillToolDecl] = []
    current_name = ""
    current_handler = ""
    for line in lines[start:]:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- "):
            if current_name and current_handler:
                decls.append(
                    SkillToolDecl(name=current_name, handler=current_handler)
                )
            current_name = ""
            current_handler = ""
            item = stripped[2:].strip()
            if item.startswith("name:"):
                current_name = item.split(":", 1)[1].strip()
            elif item.startswith("handler:"):
                current_handler = item.split(":", 1)[1].strip()
            continue
        if stripped.startswith("name:"):
            current_name = stripped.split(":", 1)[1].strip()
            continue
        if stripped.startswith("handler:"):
            current_handler = stripped.split(":", 1)[1].strip()
            continue
        if not line.startswith((" ", "\t")):
            break
    if current_name and current_handler:
        decls.append(SkillToolDecl(name=current_name, handler=current_handler))
    return decls
