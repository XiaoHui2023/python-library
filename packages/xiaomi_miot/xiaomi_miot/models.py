from typing import Any
from pydantic import BaseModel, Field, ConfigDict


class DeviceParams(BaseModel):
    """最基础的设备参数：局域网连接所需"""
    model_config = ConfigDict(extra="ignore")

    ip: str = Field(description="设备 IP 地址")
    token: str = Field(description="设备 Token")
    type: str | None = Field(default=None,description="设备类型")

class GetParams(DeviceParams):
    """通用属性读取"""
    did: str = Field(default="prop",description="默认 did：prop")
    siid: int = Field(description="service ID")
    piid: int = Field(description="property ID")


class SetParams(GetParams):
    """通用属性设置"""
    value: Any = Field(description="属性值")