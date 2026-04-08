from typing import Any

from ._base import ActionBase
from ._registry import register


@register("set_params")
class SetParamsAction(ActionBase):
    """原始参数透传（万能兜底）"""

    params: dict[str, Any]

    async def execute(self, client) -> dict[str, Any] | None:
        return await client.set_device_params(self.device, self.params)