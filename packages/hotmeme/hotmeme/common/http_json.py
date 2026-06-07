from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


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
