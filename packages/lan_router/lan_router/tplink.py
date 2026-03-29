from .base import BaseRouter
from .device import Device
from tplinkrouterc6u import TPLinkXDRClient

class TPLinkRouter(BaseRouter):
    _router: TPLinkXDRClient = None

    def model_post_init(self,ctx):
        self._router = TPLinkXDRClient(self.hostname, self.username, self.password)

    def login(self):
        self._router.authorize()

    def logout(self):
        self._router.logout()

    def scan(self) -> list[Device]:
        devices = []
        status = self._router.get_status()

        for data in status.devices:
            type = getattr(data.type, "value", str(data.type))
            name = data.hostname or ""
            ip =  self._show(data.ipaddr)
            mac = self._show(data.macaddr)
            device = Device(name=name, ip=ip, mac=mac, type=type)
            devices.append(device)

        return devices

    def _show(self, v: str | None) -> str:
        """显示空值"""
        return "-" if v is None or v == "" else v