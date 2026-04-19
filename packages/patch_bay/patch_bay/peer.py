from __future__ import annotations

from .transport.websocket import websocket_url


def canonical_peer(value: str) -> str:
    """配置里 ``jacks[].address`` 等字符串的规范化（strip）。"""
    s = str(value).strip()
    if not s:
        raise ValueError("peer address must be non-empty")
    return s


def parse_host_port(addr: str) -> tuple[str, int]:
    """解析 ``host:port`` 或 ``[IPv6]:port``，返回 ``(host, port)``（IPv6 含方括号）。"""
    s = canonical_peer(addr)
    if s.startswith("["):
        end = s.index("]")
        if "]:" not in s[end:]:
            raise ValueError(f"invalid bracketed address: {addr!r}")
        port = int(s[end + 2 :].lstrip())
        return s[: end + 1], port
    if ":" not in s:
        raise ValueError(f"expected host:port, got {addr!r}")
    host, _, port_s = s.rpartition(":")
    if not host or not port_s:
        raise ValueError(f"invalid address: {addr!r}")
    return host.strip(), int(port_s)


def ws_url_for_jack_listen(address: str, ws_path: str = "/ws") -> str:
    """``jacks[].address``（Jack 监听地址）→ PatchBay 出站 WebSocket URL。"""
    host, port = parse_host_port(address)
    if host.startswith("["):
        netloc = f"{host}:{port}"
    else:
        netloc = f"{host}:{port}"
    return websocket_url(f"ws://{netloc}", ws_path)
