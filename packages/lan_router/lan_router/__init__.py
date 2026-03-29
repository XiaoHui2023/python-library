from .device import Device
from .base import BaseRouter
from .tplink import TPLinkRouter
from typing import Literal

def create_router(vendor: Literal["tplink"],**kwargs) -> BaseRouter:
    if vendor == "tplink":
        return TPLinkRouter(**kwargs)
    else:
        raise ValueError(f"不支持的厂商: {vendor}")

__all__ = [
    "Device",
    "BaseRouter",
    "TPLinkRouter",
]