from typing import Any

from ._base import ActionBase, SwitchEntry
from ._registry import register


@register("set_outlets")
class SetOutletsAction(ActionBase):
    """同时控制多个通道"""

    switches: list[SwitchEntry]

    async def execute(self, client) -> dict[str, Any] | None:
        payload = [{"outlet": s.outlet, "switch": s.state} for s in self.switches]
        return await client.set_outlets(self.device, payload)