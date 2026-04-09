import importlib
import pkgutil
from pathlib import Path

_extensions: dict[str, type] = {}
_discovered = False


def extension(name: str):
    """装饰器：注册设备扩展

    @extension("switch")
    class SwitchExtension:
        class Params(DeviceParams): ...
        def execute(self, device, params): ...
    """
    def decorator(cls):
        _extensions[name] = cls
        return cls
    return decorator


def get_extension(name: str):
    discover()
    return _extensions.get(name)


def list_extensions() -> list[str]:
    discover()
    return list(_extensions.keys())


def discover():
    """动态扫描 extensions/ 目录下所有模块，导入以触发 @extension 注册"""
    global _discovered
    if _discovered:
        return
    _discovered = True

    ext_dir = Path(__file__).parent
    for finder, module_name, is_pkg in pkgutil.iter_modules([str(ext_dir)]):
        if module_name.startswith("_"):
            continue
        importlib.import_module(f"{__package__}.{module_name}")