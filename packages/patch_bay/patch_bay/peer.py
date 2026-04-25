from __future__ import annotations

from .transport.websocket import websocket_url


def canonical_peer(value: str) -> str:
    """规范化配置中的接入点地址。

    Args:
        value: 用户配置的地址字符串。

    Returns:
        str: 去除首尾空白后的地址。

    Raises:
        ValueError: 地址为空时抛出。
    """
    s = str(value).strip()
    if not s:
        raise ValueError("peer address must be non-empty")
    return s


def parse_host_port(addr: str) -> tuple[str, int]:
    """解析接入点地址中的主机与端口。

    Args:
        addr: `host:port` 或 `[IPv6]:port` 形式的地址。

    Returns:
        tuple[str, int]: 主机文本与端口号。

    Raises:
        ValueError: 地址缺少主机或端口时抛出。
    """
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
    """把接入点地址转换为可连接的 URL。

    Args:
        address: 用户配置的接入点地址。
        ws_path: 连接路径，默认使用协议约定路径。

    Returns:
        str: 可交给客户端连接的 URL。
    """
    host, port = parse_host_port(address)
    if host.startswith("["):
        netloc = f"{host}:{port}"
    else:
        netloc = f"{host}:{port}"
    return websocket_url(f"ws://{netloc}", ws_path)
