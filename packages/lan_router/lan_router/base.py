from pydantic import BaseModel
from abc import ABC, abstractmethod
from .device import Device

class BaseRouter(BaseModel, ABC):
    hostname: str
    """路由器主机名"""
    username: str
    """路由器用户名"""
    password: str
    """路由器密码"""

    @abstractmethod
    def scan(self) -> list[Device]:
        """扫描设备"""
        pass

    def login(self):
        """登录"""
        pass

    def logout(self):
        """登出"""
        pass