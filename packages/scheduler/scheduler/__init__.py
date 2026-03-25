from .scheduler import Scheduler

async def run_schedule():
    """运行调度器"""
    return await Scheduler().run()

__all__ = [
    "Scheduler",
]