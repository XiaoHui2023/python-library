from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr
from observer import ObserverBus

if TYPE_CHECKING:
    from automation.runtime.context import Context

observer_bus = ObserverBus()


@observer_bus.observe()
class BaseAutomation(BaseModel):
    """自动化对象基类，提供生命周期与运行时钩子。"""

    model_config = ConfigDict(validate_assignment=True)

    registered_kind: ClassVar[str | None] = None

    instance_name: str = Field(..., description="实例名")

    _ctx: Context = PrivateAttr()

    @property
    def ctx(self) -> Context:
        """当前对象绑定的运行时上下文。"""

        return self._ctx

    async def build_phase(self) -> None:
        """构建阶段：依次调用 before、主体、after。"""

        await self.before_build()
        await self.on_build()
        await self.after_build()

    async def validate_phase(self) -> None:
        """加载校验阶段：依次调用 before、主体、after。"""

        await self.before_validate()
        await self.on_validate()
        await self.after_validate()

    async def activate_phase(self) -> None:
        """激活阶段：依次调用 before、主体、after。"""

        await self.before_activate()
        await self.on_activate()
        await self.after_activate()

    async def inactive_phase(self) -> None:
        """反激活阶段：依次调用 before、主体、after。"""

        await self.before_inactive()
        await self.on_inactive()
        await self.after_inactive()

    async def run_phase(self, *, closing: bool = False) -> None:
        """运行阶段：依次调用 before、主体、after。

        Args:
            closing: 为 True 时表示运行期收尾（对应原停机路径），默认可视为进入运行期。
        """

        await self.before_run(closing=closing)
        await self.on_run(closing=closing)
        await self.after_run(closing=closing)

    async def before_build(self) -> None:
        """构建主体之前。"""

    async def on_build(self) -> None:
        """根据已绑定配置与上下文完成运行时结构初始化。"""

    async def after_build(self) -> None:
        """构建主体之后。"""

    async def before_validate(self) -> None:
        """加载校验主体之前。"""

    async def on_validate(self) -> None:
        """验证本对象在已绑定运行时环境中的配置与引用关系。"""

    async def after_validate(self) -> None:
        """加载校验主体之后。"""

    async def before_activate(self) -> None:
        """激活主体之前。"""

    async def on_activate(self) -> None:
        """激活阶段：注册回调、启动调度等。"""

    async def after_activate(self) -> None:
        """激活主体之后。"""

    async def before_inactive(self) -> None:
        """反激活主体之前。"""

    async def on_inactive(self) -> None:
        """反激活阶段：与激活阶段对称，撤销登记与钩子（重载或停机前）。"""

    async def after_inactive(self) -> None:
        """反激活主体之后。"""

    async def before_run(self, *, closing: bool = False) -> None:
        """运行主体之前；closing 为 True 时表示收尾语义。"""

    async def on_run(self, *, closing: bool = False) -> None:
        """运行期主体；closing 为 True 时表示收尾语义。"""

    async def after_run(self, *, closing: bool = False) -> None:
        """运行主体之后；closing 为 True 时表示收尾语义。"""


def registered_kind_for(cls: type[Any]) -> str | None:
    """沿 MRO 查找已登记的注册键。

    Args:
        cls: 模型类。

    Returns:
        可选字符串: 在继承链上找到已设置的注册键则返回，否则为空。
    """
    for c in cls.__mro__:
        kind = getattr(c, "registered_kind", None)
        if kind is not None:
            return kind
    return None
