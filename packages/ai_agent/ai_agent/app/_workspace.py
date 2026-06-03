from __future__ import annotations

import shutil
from pathlib import Path

_SESSIONS_DIR = "sessions"
SESSION_HARNESS_SUBDIR = "harness"
SESSION_MEMORY_SUBDIR = "memory"


def resolve_app_sandbox_root(sandbox: Path | str) -> Path:
    """
    解析并创建总沙箱根目录。

    Args:
        sandbox: 总沙箱路径

    Returns:
        规范化后的绝对路径
    """
    root = Path(sandbox).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    if not root.is_dir():
        raise ValueError(f"沙箱根须为目录: {root}")
    return root


def validate_session_id(session_id: str) -> str:
    """
    校验会话标识，拒绝路径穿越与分隔符。

    Args:
        session_id: 调用方提供的会话 id

    Returns:
        去首尾空白后的 id
    """
    cleaned = session_id.strip()
    if not cleaned:
        raise ValueError("session_id 不能为空")
    if cleaned in (".", ".."):
        raise ValueError(f"非法 session_id: {session_id}")
    for char in ("/", "\\", "\0"):
        if char in cleaned:
            raise ValueError(f"session_id 不能包含路径分隔符: {session_id}")
    return cleaned


def session_workspace(sandbox_root: Path, session_id: str) -> Path:
    """
    在总沙箱下为某会话分配子工作区目录。

    Args:
        sandbox_root: 总沙箱根（已 resolve）
        session_id: 会话 id

    Returns:
        该会话专属子目录（已创建）
    """
    label = validate_session_id(session_id)
    target = (sandbox_root / _SESSIONS_DIR / label).resolve()
    try:
        target.relative_to(sandbox_root)
    except ValueError as exc:
        raise ValueError(f"会话工作区越出总沙箱: {session_id}") from exc
    target.mkdir(parents=True, exist_ok=True)
    if not target.is_dir():
        raise ValueError(f"无法创建会话工作区: {session_id}")
    return target


def _validate_session_subdir_name(name: str, *, label: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError(f"{label} 不能为空")
    if cleaned in (".", ".."):
        raise ValueError(f"非法 {label}: {name}")
    for char in ("/", "\\", "\0"):
        if char in cleaned:
            raise ValueError(f"{label} 不能包含路径分隔符: {name}")
    return cleaned


def session_harness_workspace(session_root: Path) -> Path:
    """
    在会话工作区下分配 Harness 隔离子目录。

    Args:
        session_root: 会话根目录（已 resolve）

    Returns:
        Harness 工作区路径（已创建）
    """
    root = session_root.resolve()
    sub = _validate_session_subdir_name(
        SESSION_HARNESS_SUBDIR,
        label="harness 子目录",
    )
    target = (root / sub).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError("Harness 子目录越出会话工作区") from exc
    target.mkdir(parents=True, exist_ok=True)
    if not target.is_dir():
        raise ValueError("无法创建 Harness 工作区")
    return target


def reset_session_subdirs(session_root: Path) -> None:
    """
    清空会话内 Harness 与 memory 子目录并重建。

    Args:
        session_root: 会话根目录
    """
    root = session_root.resolve()
    for sub_name in (SESSION_HARNESS_SUBDIR, SESSION_MEMORY_SUBDIR):
        sub = _validate_session_subdir_name(sub_name, label="子目录")
        target = (root / sub).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"子目录越出会话工作区: {sub_name}") from exc
        if target.is_dir():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)
