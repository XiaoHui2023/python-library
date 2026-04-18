"""将用户给出的路径（含 glob 等灵活表达式）解析为实际监视根路径。"""

from __future__ import annotations

import glob
import os
from collections.abc import Sequence
from pathlib import Path


def _has_glob_magic(s: str) -> bool:
    return any(ch in s for ch in "*?[")


def _normalize_root(root: str | Path | None) -> Path | None:
    if root is None:
        return None
    return Path(os.path.expandvars(os.path.expanduser(str(root)))).resolve()


def _expand_user_vars(raw: str | Path) -> str:
    return os.path.expandvars(os.path.expanduser(str(raw)))


def _with_root(expanded: str, root: Path | None) -> str:
    """在 ``root`` 下拼接相对路径；已为绝对路径（含 ``~`` 展开后）则不变。"""
    p = Path(expanded)
    if root is not None and not p.is_absolute():
        p = root / p
    return str(p)


def _is_blank_path_entry(raw: str | Path) -> bool:
    """展开环境变量与 ``~`` 后无有效字符的路径条目（含纯空白）视为空，应跳过。"""
    return not _expand_user_vars(raw).strip()


def expand_watch_paths(
    paths: Sequence[str | Path],
    *,
    root: str | Path | None = None,
) -> list[Path]:
    """
    将 ``paths`` 解析为可监视的根路径列表，**不抛错**；无法解析或不适用的条目跳过。

    - 空序列返回空列表。
    - 展开环境变量与 ``~`` 后为空的条目跳过。
    - 含 ``* ? [`` 的条目：``glob.glob(..., recursive=True)``；零个匹配则本条目不贡献结果；
      有匹配则只保留已存在且为文件或目录的路径（断链、管道等跳过）。
    - 不含 glob 元字符的条目：解析后仅当路径已存在且为文件或目录时纳入，否则跳过。

    ``root``：若给出，则对 **相对路径**（展开环境变量与 ``~`` 后仍非绝对路径者）先拼到 ``root`` 下再解析；
    已是绝对路径的条目不受 ``root`` 影响。
    """
    if not paths:
        return []

    base = _normalize_root(root)
    seen: dict[str, Path] = {}

    for raw in paths:
        if _is_blank_path_entry(raw):
            continue
        expanded = _with_root(_expand_user_vars(raw), base)
        if _has_glob_magic(expanded):
            for m in glob.glob(expanded, recursive=True):
                p = Path(m).resolve(strict=False)
                if p.exists() and (p.is_file() or p.is_dir()):
                    seen[str(p)] = p
            continue

        p = Path(expanded).resolve()
        if p.exists() and (p.is_file() or p.is_dir()):
            seen[str(p)] = p

    return list(seen.values())


def watch_paths_exist(
    paths: Sequence[str | Path],
    *,
    root: str | Path | None = None,
) -> bool:
    """
    是否与 :func:`expand_watch_paths` 会给出**非空**结果等价（解析规则与 ``root`` 一致）。

    - 空序列返回 ``False``。
    - 展开后为空的条目跳过。
    - 字面路径不存在、glob 零匹配、或路径非文件/非目录：该条目不匹配。
    - 任一条目能解析出至少一个已存在的文件或目录即返回 ``True``。
    """
    return bool(expand_watch_paths(paths, root=root))
