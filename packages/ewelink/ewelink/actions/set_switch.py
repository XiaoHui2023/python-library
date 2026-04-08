from typing import Any

from ._base import ActionBase, State
from ._registry import register


@register("set_switch")
class SetSwitchAction(ActionBase):
    """控制单通道设备开关"""

    state: State

    async def execute(self, client) -> dict[str, Any] | None:
        return await client.set_switch(self.device, self.state)