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


def expand_watch_paths(
    paths: Sequence[str | Path],
    *,
    root: str | Path | None = None,
) -> list[Path]:
    """
    - 不含 glob 元字符的路径：按字面解析，必须已存在。
    - 含 ``* ? [`` 等 glob 的路径：用 ``glob.glob(..., recursive=True)`` 展开；
      仅当 **glob 返回零个匹配串** 时才报错；随后只保留已存在且为文件或目录的路径。

    ``root``：若给出，则对 **相对路径**（展开环境变量与 ``~`` 后仍非绝对路径者）先拼到 ``root`` 下再解析；
    已是绝对路径的条目不受 ``root`` 影响。
    """
    if not paths:
        raise ValueError("paths must contain at least one path")

    base = _normalize_root(root)
    seen: dict[str, Path] = {}

    for raw in paths:
        expanded = _with_root(_expand_user_vars(raw), base)
        if _has_glob_magic(expanded):
            matches = glob.glob(expanded, recursive=True)
            if not matches:
                raise FileNotFoundError(f"no paths matched pattern: {raw!r}")
            for m in matches:
                p = Path(m).resolve(strict=False)
                if p.exists() and (p.is_file() or p.is_dir()):
                    seen[str(p)] = p
            continue

        p = Path(expanded).resolve()
        if not p.exists():
            raise FileNotFoundError(f"watch path does not exist: {raw!r}")
        if not p.is_file() and not p.is_dir():
            raise ValueError(f"watch path is neither a file nor a directory: {raw!r}")
        seen[str(p)] = p

    return list(seen.values())


def watch_paths_exist(
    paths: Sequence[str | Path],
    *,
    root: str | Path | None = None,
) -> bool:
    """
    与 :func:`expand_watch_paths` 使用相同的解析规则（含可选 ``root``），但不抛错，仅判断是否能匹配到
    **至少一个**已存在的文件或目录。

    - 空序列返回 ``False``。
    - 字面路径不存在：该条目不匹配，不抛错。
    - glob 零匹配：该条目不匹配，不抛错。
    - 任一条目能解析出至少一个存在的文件或目录即返回 ``True``。
    """
    if not paths:
        return False

    base = _normalize_root(root)

    for raw in paths:
        expanded = _with_root(_expand_user_vars(raw), base)
        if _has_glob_magic(expanded):
            matches = glob.glob(expanded, recursive=True)
            for m in matches:
                p = Path(m).resolve(strict=False)
                if p.exists() and (p.is_file() or p.is_dir()):
                    return True
            continue

        p = Path(expanded).resolve()
        if p.exists() and (p.is_file() or p.is_dir()):
            return True

    return False
