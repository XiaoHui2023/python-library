from __future__ import annotations

import importlib
import pkgutil

_DISCOVERED = False


def load_syntax_modules() -> None:
    global _DISCOVERED

    if _DISCOVERED:
        return

    for module_info in pkgutil.iter_modules(__path__):
        if module_info.name.startswith("_"):
            continue
        importlib.import_module(f"{__name__}.{module_info.name}")

    _DISCOVERED = True