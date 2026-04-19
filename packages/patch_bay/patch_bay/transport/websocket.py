from __future__ import annotations

from urllib.parse import urlparse, urlunparse


def websocket_url(server: str, path: str = "/ws") -> str:
    """将 ws(s)://host:port 规范为带 path 的 URL（默认补全 /ws）。"""
    u = urlparse(server.strip())
    if u.scheme not in ("ws", "wss"):
        raise ValueError("server must use ws:// or wss://")
    p = u.path or "/"
    if p in ("/", ""):
        u = u._replace(path=path if path.startswith("/") else f"/{path}")
    return urlunparse(u)
