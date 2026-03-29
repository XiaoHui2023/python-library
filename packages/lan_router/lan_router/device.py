from pydantic import BaseModel

class Device(BaseModel):
    name: str
    """设备名称"""
    ip: str
    """设备IP地址"""
    mac: str
    """设备MAC地址"""
    type: str
    """设备类型"""