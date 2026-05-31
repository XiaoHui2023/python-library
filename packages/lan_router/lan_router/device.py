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
    active: bool = True
    """路由器报告的在线状态；未返回在线字段时视为在线"""