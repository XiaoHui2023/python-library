import inspect
from typing import ClassVar

from pydantic import Field, PrivateAttr
from automation.core import Action

class CallEntityMethod(Action):
    _abstract: ClassVar[bool] = False
    _type: ClassVar[str] = "call_entity_method"

    entity: str = Field(description="实体名称")
    method: str = Field(description="方法名称")
    args: dict = Field(default_factory=dict, description="方法参数")

    _entity = PrivateAttr(default=None)

    def validate(self, ctx):
        try:
            entity = ctx.entities[self.entity]
        except KeyError as e:
            raise ValueError(f"实体 {self.entity!r} 不存在") from e

        if not hasattr(entity, self.method):
            raise ValueError(f"实体 {self.entity} 不存在方法 {self.method}")

        method = getattr(entity, self.method)
        if not callable(method):
            raise ValueError(f"实体 {self.entity} 的方法 {self.method} 不可调用")

        try:
            inspect.signature(method).bind(**self.args)
        except TypeError as e:
            raise ValueError(f"实体 {self.entity} 的方法 {self.method} 的参数不正确") from e

        self._entity = entity

    async def run(self):
        method = getattr(self._entity, self.method)
        result = method(**self.args)
        if inspect.isawaitable(result):
            await result