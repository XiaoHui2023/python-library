import asyncio
from pathlib import Path
from automation import Assistant, ConsoleRenderer

async def main():
    assistant = Assistant(listener=ConsoleRenderer())
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