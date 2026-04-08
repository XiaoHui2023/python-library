from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ._base import ActionBase, State, SwitchEntry
from ._registry import REGISTRY, register

# ── 自动扫描：导入本目录下所有非下划线开头的 .py ──
_pkg_dir = Path(__file__).parent
for _info in pkgutil.iter_modules([str(_pkg_dir)]):
    if not _info.name.startswith("_"):
        importlib.import_module(f".{_info.name}", __package__)


def validate_task(data: dict[str, Any]) -> ActionBase:
    """校验单个任务配置，返回对应的 action 模型实例。"""
    action = data.get("action")
    if not action:
        raise ValueError("缺少必填字段 'action'")
    if action not in REGISTRY:
        supported = ", ".join(sorted(REGISTRY))
        raise ValueError(f"不支持的 action: {action!r}，当前支持: {supported}")

    payload = {k: v for k, v in data.items() if k != "action"}
    try:
        return REGISTRY[action].model_validate(payload)
    except ValidationError as e:
        raise ValueError(f"action={action!r} 校验失败:\n{e}") from None


def validate_tasks(raw_list: list[dict[str, Any]]) -> list[ActionBase]:
    """批量校验，所有错误一次性报出。"""
    results: list[ActionBase] = []
    errors: list[str] = []
    for i, raw in enumerate(raw_list, 1):
        try:
            results.append(validate_task(raw))
        except ValueError as e:
            errors.append(f"任务 #{i}: {e}")
    if errors:
        raise ValueError("配置校验失败:\n" + "\n".join(errors))
    return results


def supported_actions() -> dict[str, str]:
    """返回所有已注册的 action 及其描述。"""
    return {
        name: (cls.__doc__ or "").strip()
        for name, cls in sorted(REGISTRY.items())
    }