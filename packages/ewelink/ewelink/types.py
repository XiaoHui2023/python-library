from typing import Literal, TypedDict

SwitchState = Literal["on", "off"]


class SwitchItem(TypedDict):
    outlet: int
    switch: SwitchState