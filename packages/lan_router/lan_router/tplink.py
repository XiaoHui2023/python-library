from tplinkrouterc6u import TPLinkXDRClient

from .base import BaseRouter
from .device import Device


class _TPLinkXDRClientNoProxy(TPLinkXDRClient):
    """TP-Link 客户端；忽略 HTTP_PROXY 等环境变量，内网路由器应直连。"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._session.trust_env = False


class TPLinkRouter(BaseRouter):
    _router: TPLinkXDRClient | None = None

    def model_post_init(self, ctx) -> None:
        self._router = _TPLinkXDRClientNoProxy(
            self.hostname,
            self.username,
            self.password,
        )

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
            device = Device(
                name=name,
                ip=ip,
                mac=mac,
                type=type,
                active=data.active,
            )
            devices.append(device)

        return devices

    def _show(self, v: str | None) -> str:
        """显示空值"""
        return "-" if v is None or v == "" else v