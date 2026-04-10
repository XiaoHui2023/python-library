import asyncio
from pathlib import Path
from automation import Assistant, ConsoleListener
from automation.listeners import TraceListener
import logging

logging.basicConfig(level=logging.INFO)

async def main():
    logs_dir = Path(__file__).parent / "logs"
    assistant = Assistant(listeners=[
        ConsoleListener(),
        TraceListener(logs_dir),
    ])
    config = Path(__file__).parent / "config.yaml"
    await assistant.load(config)
    try:
        await assistant.run()
    except asyncio.CancelledError:
        pass
    finally:
        await assistant.stop()

try:
    asyncio.run(main())
except KeyboardInterrupt:
    pass