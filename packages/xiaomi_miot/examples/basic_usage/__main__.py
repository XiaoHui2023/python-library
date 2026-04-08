import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from xiaomi_miot import XiaomiMiotClient

logging.basicConfig(level=logging.DEBUG)
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


async def main():
    username = os.environ["XIAOMI_USERNAME"]
    password = os.environ["XIAOMI_PASSWORD"]
    server = os.environ.get("XIAOMI_SERVER", "cn")

    async with XiaomiMiotClient() as client:
        # 1. 登录小米账号
        auth = await client.login(username, password, server=server)
        print("Logged in:", auth["user_id"])

        # 2. 获取设备列表
        devices = await client.get_devices()
        for d in devices:
            print(
                f"  {d.get('name')}  "
                f"did={d.get('did')}  "
                f"model={d.get('model')}  "
                f"ip={d.get('localip')}"
            )

        # 3. 获取设备规范 (了解 siid/piid/aiid)
        spec = await client.get_device_spec("yeelink.light.lamp1")
        if spec:
            for srv in spec.services.values():
                print(f"\n[Service] {srv.name} (siid={srv.iid}): {srv.description}")
                for prop in srv.properties.values():
                    rw = "R" if prop.readable else ""
                    rw += "W" if prop.writeable else ""
                    print(
                        f"  {prop.name:<30} siid={srv.iid} piid={prop.iid}  "
                        f"[{rw}]  format={prop.format}"
                    )
                for act in srv.actions.values():
                    print(
                        f"  [Action] {act.name:<24} siid={srv.iid} aiid={act.iid}  "
                        f"in={act.ins} out={act.out}"
                    )

            # 打印 mapping (可直接用于 get/set_properties)
            print("\n--- Mapping ---")
            for key, val in spec.services_mapping().items():
                print(f"  {key}: {val}")

        # 4. 云端读取属性
        did = "123456789"
        result = await client.cloud_get_props(did, [
            {"siid": 2, "piid": 1},
            {"siid": 2, "piid": 2},
        ])
        print("\nCloud get props:", result)

        # 5. 云端设置属性
        result = await client.cloud_set_props(did, [
            {"siid": 2, "piid": 1, "value": True},
            {"siid": 2, "piid": 2, "value": 80},
        ])
        print("Cloud set props:", result)

        # 6. 云端执行动作
        result = await client.cloud_action(did, siid=3, aiid=1, params=[])
        print("Cloud action:", result)

        # 7. 局域网控制 (需要知道设备 IP 和 token)
        device = client.local_device("192.168.1.100", "ffffffffffffffffffffffffffffffff")
        info = await device.info()
        print("\nLocal device info:", info)

        result = await device.get_props([
            {"did": did, "siid": 2, "piid": 1},
        ])
        print("Local get props:", result)

        await device.set_props([
            {"did": did, "siid": 2, "piid": 1, "value": False},
        ])


asyncio.run(main())