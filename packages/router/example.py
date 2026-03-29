from router import TPLinkRouter
from settings import settings

if __name__ == "__main__":
    router = TPLinkRouter(
        hostname=settings.router_hostname,
        username=settings.router_username,
        password=settings.router_password
    )

    router.login()

    devices = router.scan()
    for i, device in enumerate(devices):

            print(f"[{i}] {device.name}")
            print(f"  在线状态      : {device.active}")
            print(f"  连接类型      : {device.type}")
            print(f"  主机名        : {device.name}")
            print(f"  IP            : {device.ip}")
            print(f"  MAC           : {device.mac}")

            print("-" * 90)

    router.logout()