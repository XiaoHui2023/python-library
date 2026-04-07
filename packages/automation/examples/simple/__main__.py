import asyncio
from automation import Assistant

async def main():
    assistant = Assistant()
    await assistant.load("config.yaml",watch=True)
    await assistant.run()


asyncio.run(main())