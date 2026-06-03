from __future__ import annotations

import fnmatch
from pathlib import Path

_MAX_READ_BYTES = 512 * 1024


class HarnessSandbox:
    """将相对路径限定在构造时指定的工作区根目录内。"""

    def __init__(self, workspace: Path) -> None:
        root = workspace.expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        if not root.is_dir():
            raise ValueError(f"工作区须为目录: {root}")
        self._root = root

    @property
    def root(self) -> Path:
        return self._root

    def resolve_path(self, path: str) -> Path:
        """
        解析相对工作区的路径并拒绝越界。

        Args:
            path: 相对工作区根的路径；空字符串表示工作区根

        Returns:
            解析后的绝对路径

        Raises:
            ValueError: 路径非法或越出工作区
        """
        cleaned = path.strip()
        if not cleaned or cleaned in (".", "./"):
            return self._root
        if Path(cleaned).is_absolute():
            raise ValueError("path 须为相对工作区的路径")
        target = (self._root / cleaned).resolve()
        try:
            target.relative_to(self._root)
        except ValueError as exc:
            raise ValueError(f"路径越出工作区: {path}") from exc
        return target

    def read_text_file(self, path: str, offset: int = 1, limit: int = 0) -> str:
        """
        读取文本文件片段。

        Args:
            path: 相对工作区路径
            offset: 起始行号，从 1 起
            limit: 最多读取行数；0 表示读到文件末尾

        Returns:
            带行号前缀的文本
        """
        if offset < 1:
            raise ValueError("offset 须 >= 1")
        if limit < 0:
            raise ValueError("limit 须 >= 0")
        target = self.resolve_path(path)
        if not target.is_file():
            raise ValueError(f"不是文件: {path}")
        size = target.stat().st_size
        if size > _MAX_READ_BYTES:
            raise ValueError(f"文件过大（>{_MAX_READ_BYTES} 字节）: {path}")
        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        start = offset - 1
        if start >= len(lines):
            return ""
        if limit > 0:
            chunk = lines[start : start + limit]
        else:
            chunk = lines[start:]
        width = len(str(start + len(chunk)))
        numbered: list[str] = []
        for index, line in enumerate(chunk, start=offset):
            numbered.append(f"{index:>{width}}|{line}")
        return "\n".join(numbered)

    def write_text_file(self, path: str, content: str, append: bool = False) -> str:
        """
        写入或追加文本文件。

        Args:
            path: 相对工作区路径
            content: 写入内容
            append: 为 True 时追加，否则覆盖

        Returns:
            简短结果说明
        """
        target = self.resolve_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        with target.open(mode, encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        action = "已追加" if append else "已写入"
        return f"{action} {len(content)} 字符到 {path}"

    def list_entries(
        self,
        path: str = "",
        *,
        max_entries: int = 200,
        pattern: str = "",
    ) -> list[str]:
        """
        列出工作区内相对路径（文件与目录）。

        Args:
            path: 相对工作区根的子目录；空表示整棵工作区
            max_entries: 最多返回条数
            pattern: 可选 glob 片段，仅保留路径匹配者

        Returns:
            相对路径列表，字典序
        """
        if max_entries < 1:
            raise ValueError("max_entries 须 >= 1")
        base = self.resolve_path(path)
        if not base.is_dir():
            raise ValueError(f"不是目录: {path or '.'}")
        entries: list[str] = []
        for item in sorted(base.rglob("*")):
            rel = item.relative_to(self._root).as_posix()
            if item.is_dir():
                rel = f"{rel}/"
            if pattern.strip() and not fnmatch.fnmatch(rel, pattern.strip()):
                continue
            entries.append(rel)
            if len(entries) >= max_entries:
                break
        if not path.strip() and not entries:
            entries.append("./")
        return entries
