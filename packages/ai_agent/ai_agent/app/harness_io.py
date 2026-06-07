from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

_INCOMING_DIR = "incoming"

_TEXT_SUFFIXES = frozenset(
    {
        ".txt",
        ".md",
        ".json",
        ".jsonl",
        ".csv",
        ".tsv",
        ".xml",
        ".html",
        ".htm",
        ".yaml",
        ".yml",
        ".ini",
        ".cfg",
        ".log",
        ".py",
        ".js",
        ".ts",
        ".css",
        ".sql",
    },
)
_IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".ico"})
_AUDIO_SUFFIXES = frozenset({".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"})
_VIDEO_SUFFIXES = frozenset({".mp4", ".mkv", ".webm", ".mov", ".avi", ".flv", ".wmv"})

_KIND_LABELS = {
    "text": "文本",
    "image": "图片",
    "audio": "音频",
    "video": "视频",
    "other": "其它",
}


@dataclass(frozen=True)
class StagedFile:
    """复制到 Harness 工作区后的单个附件摘要。"""

    rel_path: str
    filename: str
    kind: str
    size_bytes: int


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


def classify_file_kind(path: Path) -> str:
    """
    按扩展名推断附件类型。

    Args:
        path: 文件路径

    Returns:
        ``text``、``image``、``audio``、``video`` 或 ``other``
    """
    suffix = path.suffix.lower()
    if suffix in _TEXT_SUFFIXES:
        return "text"
    if suffix in _IMAGE_SUFFIXES:
        return "image"
    if suffix in _AUDIO_SUFFIXES:
        return "audio"
    if suffix in _VIDEO_SUFFIXES:
        return "video"
    return "other"


def stage_input_files(
    source_paths: tuple[str, ...],
    harness_root: Path,
) -> tuple[StagedFile, ...]:
    """
    将用户文件复制到 Harness 的 incoming/ 子目录。

    Args:
        source_paths: 源文件路径列表
        harness_root: Harness 沙箱根

    Returns:
        复制后各附件的摘要（相对路径、类型、大小等）

    Raises:
        ValueError: 源路径不存在或不是文件
    """
    if not source_paths:
        return ()
    incoming = harness_root / _INCOMING_DIR
    incoming.mkdir(parents=True, exist_ok=True)
    staged: list[StagedFile] = []
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
        staged.append(
            StagedFile(
                rel_path=rel,
                filename=name,
                kind=classify_file_kind(source),
                size_bytes=target.stat().st_size,
            ),
        )
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


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KiB"
    return f"{size_bytes / (1024 * 1024):.1f} MiB"


def format_input_files_context(staged: tuple[StagedFile, ...]) -> str:
    """
    生成拼入规划与执行阶段的附件说明。

    用户文字里可能未提到文件名；此处列出本轮全部附件及处理指引。
    """
    if not staged:
        return ""
    lines = [
        "## 用户附件（已复制到 Harness 工作区）",
        "",
        "用户可能未在文字里提到文件名；以下为本轮传入的全部附件（路径均相对工作区根）：",
        "",
    ]
    for item in staged:
        label = _KIND_LABELS.get(item.kind, item.kind)
        lines.append(
            f"- `{item.rel_path}` · 类型：{label} · 大小：{_format_size(item.size_bytes)}",
        )
    lines.extend(
        [
            "",
            "## 附件处理指引",
            "",
            "- 文本类附件：用 `harness__read_file` 读取上表路径。",
            "- 图片、音视频或需深度分析的文件：用 MCP 工具 `cursor_cli__run_cursor_agent`；"
            "`workspace` 填 Harness 工作区路径，`image_paths` / `context_paths` 填相对该 workspace 的路径。",
            "- 可用 `harness__run_python` / `harness__run_shell` 做格式转换或提取元数据。",
            "- 产出须交还给用户的文件：先写入工作区（如 `out/结果.png`），"
            "最后在交付 JSON 的 `output_files` 中列出相对路径；可含图片、音视频等任意类型。",
            "- 所有路径均相对 Harness 工作区根，勿使用宿主机绝对路径。",
        ],
    )
    return "\n".join(lines)


def compose_user_message_with_attachments(
    request: str,
    staged: tuple[StagedFile, ...],
    file_context: str,
) -> str:
    """
    拼规划与记忆用的用户原文（不含最终交付 JSON 说明）。

    仅传附件而无文字时，补默认说明以便模型理解任务。
    """
    req = request.strip()
    if not req and staged:
        req = "（用户未附带文字说明，仅提交了附件。）请根据附件内容理解并完成用户可能隐含的请求。"
    parts: list[str] = [req] if req else []
    if file_context.strip():
        parts.append(file_context.strip())
    return "\n\n".join(parts)
