"""需配置 .env 与真实路由器，在包根目录执行: python tests/router_scan_demo.py"""

from lan_router import create_router
from settings import settings

if __name__ == "__main__":
    router = create_router(
        settings.router_vendor,
        hostname=settings.router_hostname,
        username=settings.router_username,
        password=settings.router_password,
    )

    router.login()

    devices = router.scan()
    for i, device in enumerate(devices):
        print(f"[{i}] {device.name}")
        print(f"  连接类型      : {device.type}")
        print(f"  主机名        : {device.name}")
        print(f"  IP            : {device.ip}")
        print(f"  MAC           : {device.mac}")
        print("-" * 90)

    router.logout()
