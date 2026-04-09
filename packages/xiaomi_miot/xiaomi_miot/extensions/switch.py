from pydantic import BaseModel, Field
from xiaomi_miot.device import MiotDevice
from xiaomi_miot.extensions import extension
from xiaomi_miot.models import DeviceParams

class SwitchParams(DeviceParams):
    type: str = "switch"
    on: bool | None = Field(default=None,description="None=查询状态, True=开, False=关")
    siid: int = Field(default=2,description="默认 service：Switch")
    piid: int = Field(default=1,description="默认 property：On")

@extension("switch")
class SwitchExtension:
    Params = SwitchParams

    def execute(self, device: MiotDevice, params: SwitchParams) -> dict:
        if params.on is None:
            return self._get_state(device, params)
        return self._set_state(device, params)

    def _get_state(self, device: MiotDevice, params: SwitchParams) -> dict:
        result = device.get_prop("switch", params.siid, params.piid)
        if result["ok"]:
            result["state"] = "开启" if result["value"] else "关闭"
        return result

    def _set_state(self, device: MiotDevice, params: SwitchParams) -> dict:
        result = device.set_prop("switch", params.siid, params.piid, params.on)
        if result["ok"]:
            result["state"] = "开启" if params.on else "关闭"
        return result