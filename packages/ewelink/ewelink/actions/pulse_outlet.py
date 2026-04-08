from typing import Any

from pydantic import Field

from ._base import ActionBase
from ._registry import register


@register("pulse_outlet")
class PulseOutletAction(ActionBase):
    """脉冲控制（开→等待→关）"""

    outlet: int
    hold_seconds: float = Field(default=0.5, gt=0)

    async def execute(self, client) -> dict[str, Any] | None:
        await client.pulse_outlet(self.device, self.outlet, self.hold_seconds)
        return None