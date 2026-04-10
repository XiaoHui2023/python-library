import importlib
import pkgutil
from pathlib import Path

def _auto_import():
    """自动导入 builtins 下所有子模块，触发类的注册"""
    package_dir = Path(__file__).resolve().parent
    for sub_pkg in package_dir.iterdir():
        if not sub_pkg.is_dir() or sub_pkg.name.startswith("_"):
            continue
        sub_package = f"{__name__}.{sub_pkg.name}"
        try:
            pkg = importlib.import_module(sub_package)
        except ImportError:
            continue
        pkg_path = getattr(pkg, "__path__", None)
        if pkg_path is None:
            continue
        for _finder, module_name, _is_pkg in pkgutil.walk_packages(
            pkg_path, prefix=f"{sub_package}."
        ):
            try:
                importlib.import_module(module_name)
            except ImportError:
                pass

_auto_import()