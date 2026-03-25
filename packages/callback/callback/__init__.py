from __future__ import annotations
from typing import ClassVar, Callable, TypeVar
import asyncio
import logging

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

    def __init__(self, *args, **kwargs):
        """初始化"""
        if len(args) == 1 and not kwargs and callable(args[0]):
            func = args[0]
            if self._async != asyncio.iscoroutinefunction(func):
                raise ValueError(f"函数{func}是{'异步' if asyncio.iscoroutinefunction(func) else '同步'}，但回调{self.__class__.__name__}是{'异步' if self._async else '同步'}")
            self.register(func)
        else:
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
            cls.function_registry[cls.__name__].append(func)
        except Exception as e:
            logger.exception(f"注册函数{func}失败: {e}")
            raise e

    @classmethod
    def trigger(cls:type[T],*args,**kwargs) -> T:
        """同步触发回调"""
        try:
            self = cls(*args, **kwargs)

            for func in cls.function_registry.get(cls.__name__, []):
                func(self)
            return self
        except Exception as e:
            logger.exception(f"触发回调{cls}失败: {e}")
            raise e

    @classmethod
    async def atrigger(cls:type[T],*args,**kwargs) -> T:
        """异步触发回调"""
        try:
            self = cls(*args, **kwargs)

            for func in cls.function_registry.get(cls.__name__, []):
                await func(self)
            return self
        except Exception as e:
            logger.exception(f"异步触发回调{cls}失败: {e}")
            raise e

    @classmethod
    def get_all(cls) -> list[type[Callback]]:
        """获取所有回调"""
        return list(cls.__subclasses__())

__all__ = [
    "Callback",
]