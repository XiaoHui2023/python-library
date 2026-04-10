from __future__ import annotations
import json
from pathlib import Path
from typing import TYPE_CHECKING

from .base import BaseListener

if TYPE_CHECKING:
    from automation.hub import Hub


class TypeSchemaListener(BaseListener):
    """加载后输出类型 schema 到文件，告诉用户怎么写配置"""

    def __init__(self, output_path: str | Path):
        self._output_path = Path(output_path)

    def on_loaded(self, hub: Hub) -> None:
        from automation.schema import export_type_schema

        schema = export_type_schema()
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        self._output_path.write_text(
            json.dumps(schema, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )