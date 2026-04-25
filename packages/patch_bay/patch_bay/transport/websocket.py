from __future__ import annotations

from urllib.parse import urlparse, urlunparse


def websocket_url(server: str, path: str = "/ws") -> str:
    """补齐连接地址中的默认路径。

    Args:
        server: 用户提供的连接地址。
        path: 地址未包含路径时使用的默认路径。

    Returns:
        str: 可直接用于连接的完整地址。

    Raises:
        ValueError: 地址协议不受支持时抛出。
    """
    u = urlparse(server.strip())
    if u.scheme not in ("ws", "wss"):
        raise ValueError("server must use ws:// or wss://")
    p = u.path or "/"
    if p in ("/", ""):
        u = u._replace(path=path if path.startswith("/") else f"/{path}")
    return urlunparse(u)
