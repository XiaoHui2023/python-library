from __future__ import annotations

import shutil
from pathlib import Path

_INCOMING_DIR = "incoming"


def reset_harness_workspace(harness_root: Path) -> None:
    """
    清空 Harness 工作区并重建空目录。

    Args:
        harness_root: Harness 沙箱根
    """
    root = harness_root.resolve()
    if root.is_dir():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)


def stage_input_files(
    source_paths: tuple[str, ...],
    harness_root: Path,
) -> tuple[str, ...]:
    """
    将用户文件复制到 Harness 的 incoming/ 子目录。

    Args:
        source_paths: 源文件路径列表
        harness_root: Harness 沙箱根

    Returns:
        复制后相对于 Harness 根的路径（incoming/文件名）

    Raises:
        ValueError: 源路径不存在或不是文件
    """
    if not source_paths:
        return ()
    incoming = harness_root / _INCOMING_DIR
    incoming.mkdir(parents=True, exist_ok=True)
    staged: list[str] = []
    used_names: set[str] = set()
    for raw in source_paths:
        source = Path(raw).expanduser().resolve()
        if not source.is_file():
            raise ValueError(f"输入文件不存在或不是文件: {raw}")
        name = source.name
        if name in used_names:
            stem = source.stem
            suffix = source.suffix
            index = 2
            while name in used_names:
                name = f"{stem}_{index}{suffix}"
                index += 1
        used_names.add(name)
        target = incoming / name
        shutil.copy2(source, target)
        rel = f"{_INCOMING_DIR}/{name}"
        staged.append(rel)
    return tuple(staged)


def resolve_output_files(
    relative_paths: tuple[str, ...],
    harness_root: Path,
) -> tuple[str, ...]:
    """
    将模型给出的相对路径解析为存在的宿主机绝对路径。

    Args:
        relative_paths: 相对 Harness 根的路径
        harness_root: Harness 沙箱根

    Returns:
        仅包含已存在常规文件的路径
    """
    root = harness_root.resolve()
    resolved: list[str] = []
    for raw in relative_paths:
        cleaned = raw.strip().replace("\\", "/")
        if not cleaned:
            continue
        if Path(cleaned).is_absolute():
            candidate = Path(cleaned).resolve()
            try:
                candidate.relative_to(root)
            except ValueError:
                continue
        else:
            candidate = (root / cleaned).resolve()
            try:
                candidate.relative_to(root)
            except ValueError:
                continue
        if candidate.is_file():
            resolved.append(str(candidate))
    return tuple(resolved)


def format_input_files_context(staged_paths: tuple[str, ...]) -> str:
    """生成拼入规划或用户消息的附件说明。"""
    if not staged_paths:
        return ""
    lines = ["## 用户附件（位于 Harness 工作区内）"]
    for rel in staged_paths:
        lines.append(f"- {rel}")
    return "\n".join(lines)
