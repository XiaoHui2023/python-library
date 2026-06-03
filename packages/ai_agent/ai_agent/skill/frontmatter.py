from __future__ import annotations

import re

_FRONTMATTER_RE = re.compile(
    r"\A---\r?\n(.*?)\r?\n---\r?\n?",
    re.DOTALL,
)


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """
    拆分 YAML frontmatter 与正文。

    Args:
        text: 完整文件内容

    Returns:
        元数据键值对与正文（无 frontmatter 时元数据为空 dict）
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    meta = _parse_simple_yaml(match.group(1))
    body = text[match.end() :]
    return meta, body


def compose_skill_md(meta: dict[str, str], body: str) -> str:
    """
    组装带 frontmatter 的 SKILL.md 文本。

    Args:
        meta: 元数据；空 dict 时不写 frontmatter
        body: Markdown 正文

    Returns:
        完整文件内容
    """
    normalized_body = body
    if normalized_body and not normalized_body.endswith("\n"):
        normalized_body += "\n"
    if not meta:
        return normalized_body
    lines = ["---"]
    for key in sorted(meta.keys()):
        lines.append(f"{key}: {_yaml_scalar(meta[key])}")
    lines.append("---")
    lines.append("")
    if normalized_body:
        return "\n".join(lines) + "\n" + normalized_body.lstrip("\n")
    return "\n".join(lines) + "\n"


def _parse_simple_yaml(block: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        key = key.strip()
        value = value.strip()
        if value.startswith('"') and value.endswith('"') and len(value) >= 2:
            value = value[1:-1]
        elif value.startswith("'") and value.endswith("'") and len(value) >= 2:
            value = value[1:-1]
        if key:
            meta[key] = value
    return meta


def _yaml_scalar(value: str) -> str:
    if not value:
        return '""'
    if re.search(r"[\n:#\"'\\]", value):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if re.search(r"[^\w.\-/]", value):
        return f'"{value}"'
    return value
