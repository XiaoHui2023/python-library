from __future__ import annotations
from typing import ClassVar, Callable, TypeVar
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)
T = TypeVar("T", bound="Callback")

class Callback():
    """
    回调

    定义回调结构时：
        class A(Callback):
            attr: type

    触发回调时：
        cb = A.trigger(attr=value) # 同步
        cb = await A.atrigger(attr=value) # 异步

    为函数注册回调时：
        @A
        def func(cb:A):
            pass
    """
    function_registry: ClassVar[dict[str, list[Callable]]] = {}
    """注册的函数列表"""
    _async: ClassVar[bool] = False
    """是否异步"""

    def __new__(cls, *args, **kwargs):
        """支持把 Callback 子类直接当装饰器使用"""
        if len(args) == 1 and not kwargs and callable(args[0]):
            func = args[0]
            if cls._async != asyncio.iscoroutinefunction(func):
                raise ValueError(
                    f"函数{func}是{'异步' if asyncio.iscoroutinefunction(func) else '同步'}，"
                    f"但回调{cls.__name__}是{'异步' if cls._async else '同步'}"
                )
            cls.register(func)
            return func
        return super().__new__(cls)

    def __init__(self, *args, **kwargs):
        """初始化事件实例"""
        field_names = list(self.__class__.__annotations__.keys())
        for i, arg in enumerate(args):
            if i < len(field_names):
                setattr(self, field_names[i], arg)
            else:
                raise ValueError(f"参数过多[{i}]: {arg}")
        for key, value in kwargs.items():
            if key in field_names:
                setattr(self, key, value)
            else:
                raise ValueError(f"未知属性[{key}]: {value}")

    @classmethod
    def register(cls, func: Callable):
        """注册函数"""
        try:
            if cls.__name__ not in cls.function_registry:
                cls.function_registry[cls.__name__] = []
            if func not in cls.function_registry[cls.__name__]:
                cls.function_registry[cls.__name__].append(func)
        except Exception as e:
            logger.exception(f"注册函数{func}失败: {e}")
            raise e

    @classmethod
    def trigger(cls:type[T],*args,**kwargs) -> T:
        """同步触发回调"""
        try:
            self = cls(*args, **kwargs)

            self.before_trigger()
            funcs = cls.function_registry.get(cls.__name__, [])
            with ThreadPoolExecutor() as executor:
                futures = [executor.submit(func, self) for func in funcs]
                for future in futures:
                    future.result()
            self.after_trigger()

            return self
        except Exception as e:
            logger.exception(f"触发回调{cls}失败: {e}")
            raise e

    @classmethod
    async def atrigger(cls:type[T],*args,**kwargs) -> T:
        """异步触发回调"""
        try:
            self = cls(*args, **kwargs)

            await self.before_atrigger()
            funcs = cls.function_registry.get(cls.__name__, [])
            tasks = [func(self) for func in funcs]
            if tasks:
                await asyncio.gather(*tasks)
            await self.after_atrigger()

            return self
        except Exception as e:
            logger.exception(f"异步触发回调{cls}失败: {e}")
            raise e

    def before_trigger(self) -> None:
        """同步触发前钩子"""
        pass

    async def before_atrigger(self) -> None:
        """异步触发前钩子"""
        pass

    def after_trigger(self) -> None:
        """同步触发后钩子"""
        pass

    async def after_atrigger(self) -> None:
        """异步触发后钩子"""
        pass

    @classmethod
    def get_all(cls) -> list[type[Callback]]:
        """获取所有回调"""
        return list(cls.__subclasses__())

__all__ = [
    "Callback",
]