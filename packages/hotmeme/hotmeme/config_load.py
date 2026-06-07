from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from hotmeme.models import HotMemeModels


def load_config(path: Path | str) -> HotMemeModels:
    """从 YAML 或 JSON 文件载入配置。

    Args:
        path: 配置文件路径。

    Returns:
        校验后的根配置模型。
    """
    file_path = Path(path).expanduser()
    text = file_path.read_text(encoding="utf-8")
    suffix = file_path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        raw: Any = yaml.safe_load(text)
    elif suffix == ".json":
        raw = json.loads(text)
    else:
        raise ValueError(f"不支持的配置格式: {file_path.suffix}")
    if raw is None:
        raw = {}
    return HotMemeModels.model_validate(raw)
