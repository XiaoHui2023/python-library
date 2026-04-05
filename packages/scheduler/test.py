from scheduler import run_schedule
from scheduler.job import Every
import asyncio

@Every(seconds=1,max_runs=3)
def test():
    print("test")

if __name__ == "__main__":
    asyncio.run(run_schedule())