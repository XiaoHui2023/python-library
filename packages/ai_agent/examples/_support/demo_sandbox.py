from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from ai_agent.app._workspace import (
    reset_session_subdirs,
    resolve_app_sandbox_root,
    session_workspace,
)
from ai_agent.app.session_store import clear_conversation


def session_ids_in_script(
    steps: Iterable[tuple[str, str, str, bool]],
) -> tuple[str, ...]:
    """
    从示例脚本步元组中提取不重复的 session_id（保持首次出现顺序）。

    Args:
        steps: ``(session_id, user_name, request, clear)`` 序列

    Returns:
        去重后的会话 id 元组
    """
    seen: set[str] = set()
    ordered: list[str] = []
    for session_id, *_rest in steps:
        if session_id in seen:
            continue
        seen.add(session_id)
        ordered.append(session_id)
    return tuple(ordered)


def clear_demo_sessions(sandbox: Path | str, session_ids: Iterable[str]) -> None:
    """
    清空示例用到的各会话：Harness、memory 子目录与无 Memory 时的对话文件。

    Args:
        sandbox: 示例 ``.sandbox`` 根
        session_ids: 须重置的会话 id
    """
    root = resolve_app_sandbox_root(sandbox)
    for session_id in session_ids:
        session_root = session_workspace(root, session_id)
        reset_session_subdirs(session_root)
        clear_conversation(session_root)
