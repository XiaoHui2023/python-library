from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


def read_http_error_payload(exc: urllib.error.HTTPError) -> dict[str, Any] | None:
    """读取 HTTP 错误响应体并尽量解析为 JSON 对象。"""
    try:
        raw = exc.read()
    except OSError:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        text = raw.decode("utf-8", errors="replace").strip()
        return {"_raw": text} if text else None
    if isinstance(payload, dict):
        return payload
    return {"_raw": payload}


def message_from_error_payload(payload: dict[str, Any] | None) -> str | None:
    """从 TikHub 错误 JSON 提取简短说明。"""
    if payload is None:
        return None
    detail = payload.get("detail")
    if isinstance(detail, dict):
        zh = detail.get("message_zh")
        en = detail.get("message")
        if zh or en:
            return str(zh or en)
    message = payload.get("message_zh") or payload.get("message")
    if message:
        return str(message)
    raw = payload.get("_raw")
    if raw is not None:
        return str(raw)
    return None


def http_error_detail_message(exc: urllib.error.HTTPError) -> str | None:
    """从 HTTP 错误响应体提取可读说明。

    Args:
        exc: ``urlopen`` 抛出的 HTTP 错误。

    Returns:
        响应 JSON 中的 ``message_zh`` / ``message``；无法解析时为 ``None``。
    """
    return message_from_error_payload(read_http_error_payload(exc))


def get_json(
    url: str,
    *,
    timeout: float,
    headers: dict[str, str] | None = None,
) -> Any:
    """GET 请求并解析 JSON 响应。

    Args:
        url: 请求地址。
        timeout: 超时秒数。
        headers: 可选请求头。

    Returns:
        解析后的 JSON 值。

    Raises:
        urllib.error.URLError: 网络或 HTTP 错误。
        json.JSONDecodeError: 响应体不是合法 JSON。
    """
    request = urllib.request.Request(url, headers=headers or {}, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
    return json.loads(body)


def post_json(
    url: str,
    *,
    timeout: float,
    headers: dict[str, str] | None = None,
    body: bytes,
) -> Any:
    """POST JSON 请求并解析响应。

    Args:
        url: 请求地址。
        timeout: 超时秒数。
        headers: 可选请求头。
        body: JSON 请求体字节。

    Returns:
        解析后的 JSON 值。

    Raises:
        urllib.error.URLError: 网络或 HTTP 错误。
        json.JSONDecodeError: 响应体不是合法 JSON。
    """
    request = urllib.request.Request(url, data=body, headers=headers or {}, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read()
    return json.loads(payload)
