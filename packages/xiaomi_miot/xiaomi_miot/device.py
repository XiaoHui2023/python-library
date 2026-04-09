from miio import Device


class MiotDevice:
    """纯局域网 MIoT 设备操作，不依赖云端"""

    def __init__(self, ip: str, token: str):
        self._dev = Device(ip, token)

    def info(self) -> dict:
        """获取设备基本信息（model, firmware, hardware 等）"""
        raw = self._dev.info()
        return {
            "model": raw.model,
            "mac": raw.mac_address,
            "firmware": raw.firmware_version,
            "hardware": raw.hardware_version,
            "raw": str(raw),
        }

    def get_prop(self, did: str, siid: int, piid: int) -> dict:
        results = self._dev.send("get_properties", [
            {"did": did, "siid": siid, "piid": piid}
        ])
        r = results[0]
        if r.get("code") == 0:
            return {"ok": True, "value": r["value"]}
        return {"ok": False, "error": r}

    def get_props(self, props: list[dict]) -> list[dict]:
        return self._dev.send("get_properties", props)

    def set_prop(self, did: str, siid: int, piid: int, value) -> dict:
        results = self._dev.send("set_properties", [
            {"did": did, "siid": siid, "piid": piid, "value": value}
        ])
        r = results[0]
        if r.get("code") == 0:
            return {"ok": True}
        return {"ok": False, "error": r}

    def set_props(self, props: list[dict]) -> list[dict]:
        return self._dev.send("set_properties", props)

    def call_action(self, did: str, siid: int, aiid: int, params: list | None = None) -> dict:
        return self._dev.send("action", {
            "did": did, "siid": siid, "aiid": aiid, "in": params or []
        })