import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from ewelink import EWeLinkClient, infer_country_code


async def main():
    load_dotenv(".env")

    email = os.environ["EWELINK_EMAIL"]
    password = os.environ["EWELINK_PASSWORD"]
    region = os.environ.get("EWELINK_REGION")

    async with EWeLinkClient() as client:
        await client.login(
            username=email,
            password=password,
            country_code=infer_country_code(email),
            region=region,
        )

        devices = await client.get_devices()
        for d in devices:
            name = d.get("name")
            device_id = d.get("deviceid")

            device = await client.get_device(device_id)
            print(f"[{name}-{device_id}]: \n{device}")


if __name__ == "__main__":
    asyncio.run(main())