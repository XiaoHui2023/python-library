import asyncio
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

from ewelink import EWeLinkClient, infer_country_code, validate_tasks


async def main() -> None:
    load_dotenv(".env")

    tasks_file = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path(__file__).with_name("config.yaml")
    )
    if not tasks_file.exists():
        print(f"Tasks file not found: {tasks_file}")
        sys.exit(1)

    config = yaml.safe_load(tasks_file.read_text(encoding="utf-8"))
    tasks = validate_tasks(config.get("tasks", []))

    async with EWeLinkClient() as client:
        await client.login(
            username=os.environ["EWELINK_EMAIL"],
            password=os.environ["EWELINK_PASSWORD"],
            country_code=infer_country_code(os.environ["EWELINK_EMAIL"]),
            region=os.environ.get("EWELINK_REGION"),
        )

        for i, task in enumerate(tasks, 1):
            print(f"[{i}/{len(tasks)}] device={task.device} action={task.action_name} ...", end=" ")
            try:
                await task.execute(client)
                print("OK")
            except Exception as exc:
                print(f"FAILED: {exc}")


if __name__ == "__main__":
    asyncio.run(main())