from __future__ import annotations

import os
import tempfile
from pathlib import Path

from pydantic import BaseModel


def atomic_write_json(path: Path, model: BaseModel, *, indent: int | None = 2) -> None:
    """将模型序列化为 JSON 并原子替换目标文件。"""
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = model.model_dump_json(indent=indent)
    data = payload.encode("utf-8")
    fd, tmp_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=path.name,
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
