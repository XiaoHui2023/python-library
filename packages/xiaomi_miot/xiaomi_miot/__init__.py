import warnings
warnings.filterwarnings("ignore", category=FutureWarning, module=r"miio\.miot_device")

from .device import MiotDevice
from .models import DeviceParams, GetParams, SetParams
from .extensions import get_extension, list_extensions
from ._api import execute

__all__ = [
    "MiotDevice",
    "DeviceParams",
    "GetParams",
    "SetParams",
    "get_extension",
    "list_extensions",
    "execute",
]