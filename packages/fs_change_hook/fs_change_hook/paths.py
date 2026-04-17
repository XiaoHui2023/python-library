"""将用户给出的路径（含 glob 等灵活表达式）解析为实际监视根路径。"""

from __future__ import annotations

import glob
import os
from collections.abc import Sequence
from pathlib import Path


def _has_glob_magic(s: str) -> bool:
    return any(ch in s for ch in "*?[")


def expand_watch_paths(paths: Sequence[str | Path]) -> list[Path]:
    """
    - 不含 glob 元字符的路径：按字面解析，必须已存在。
    - 含 ``* ? [`` 等 glob 的路径：用 ``glob.glob(..., recursive=True)`` 展开；
      仅当 **glob 返回零个匹配串** 时才报错；随后只保留已存在且为文件或目录的路径。
    """
    if not paths:
        raise ValueError("paths must contain at least one path")

    seen: dict[str, Path] = {}

    for raw in paths:
        expanded = os.path.expandvars(os.path.expanduser(str(raw)))
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
