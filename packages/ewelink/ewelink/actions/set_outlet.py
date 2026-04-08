from typing import Any

from ._base import ActionBase, State
from ._registry import register


@register("set_outlet")
class SetOutletAction(ActionBase):
    """控制多通道设备的某一个通道"""

    outlet: int
    state: State

    async def execute(self, client) -> dict[str, Any] | None:
        return await client.set_outlet(self.device, self.outlet, self.state)