from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, ClassVar

from pydantic import BaseModel, BeforeValidator, ConfigDict

if TYPE_CHECKING:
    from ..client import EWeLinkClient


def _normalize_state(v: Any) -> str:
    """YAML 会把 on/off 解析为 True/False，在此统一转回字符串。"""
    if v is True:
        return "on"
    if v is False:
        return "off"
    if v in ("on", "off"):
        return v
    raise ValueError(f"无效值 {v!r}，应为 'on' 或 'off'")


State = Annotated[str, BeforeValidator(_normalize_state)]


class SwitchEntry(BaseModel):
    outlet: int
    state: State


class ActionBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_name: ClassVar[str] = ""
    device: str

    async def execute(self, client: EWeLinkClient) -> dict[str, Any] | None:
        raise NotImplementedError