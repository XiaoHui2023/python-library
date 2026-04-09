from .device import MiotDevice
from .models import DeviceParams, GetParams, SetParams
from .extensions import get_extension, list_extensions


def execute(params: dict) -> dict:
    """统一入口，用户输入永远是 dict

    通用模式（无 type）:
        {"ip": "...", "token": "...", "siid": 2, "piid": 1}              → 读属性
        {"ip": "...", "token": "...", "siid": 2, "piid": 1, "value": 1}  → 写属性
        {"ip": "...", "token": "...", "action": "info"}                   → 设备信息

    扩展模式（有 type）:
        {"type": "switch", "ip": "...", "token": "...", "on": True}       → 走开关扩展
    """
    device_type = params.get("type")

    if device_type:
        return _execute_extension(device_type, params)
    return _execute_generic(params)


def _execute_extension(device_type: str, params: dict) -> dict:
    ext_cls = get_extension(device_type)
    if ext_cls is None:
        return {
            "ok": False,
            "error": f"未知设备类型: {device_type}",
            "available": list_extensions(),
        }

    ext = ext_cls()
    validated = ext.Params(**params)
    device = MiotDevice(validated.ip, validated.token)
    return ext.execute(device, validated)


def _execute_generic(params: dict) -> dict:
    action = params.get("action", "prop")

    if action == "info":
        dp = DeviceParams(**params)
        device = MiotDevice(dp.ip, dp.token)
        return {"ok": True, **device.info()}

    if "value" in params:
        sp = SetParams(**params)
        device = MiotDevice(sp.ip, sp.token)
        return device.set_prop(sp.did, sp.siid, sp.piid, sp.value)

    gp = GetParams(**params)
    device = MiotDevice(gp.ip, gp.token)
    return device.get_prop(gp.did, gp.siid, gp.piid)