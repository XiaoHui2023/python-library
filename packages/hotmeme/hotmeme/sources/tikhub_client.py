from __future__ import annotations

import json
import urllib.error
from typing import Any
from urllib.parse import urlencode

from hotmeme.common.errors import TikHubApiError
from hotmeme.models import TikHubApiCall
from hotmeme.common.http_json import (
    get_json,
    message_from_error_payload,
    post_json,
    read_http_error_payload,
)


class TikHubClient:
    """TikHub HTTP 客户端。"""

    _DEFAULT_HEADERS = {
        "User-Agent": "hotmeme",
        "Accept": "application/json",
    }

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.tikhub.io",
        timeout: float = 5.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self.request_log: list[TikHubApiCall] = []

    def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        timeout: float | None = None,
    ) -> Any:
        """发起 GET 请求并返回 ``data`` 字段。

        Args:
            path: API 路径，如 ``/api/v1/xiaohongshu/...``。
            params: 查询参数。
            timeout: 覆盖默认超时秒数。

        Returns:
            响应体中的 ``data``。

        Raises:
            TikHubApiError: 响应码非 200 或缺少 data。
        """
        query = ""
        request_params = dict(params) if params else None
        if params:
            filtered = {key: value for key, value in params.items() if value is not None}
            if filtered:
                query = "?" + urlencode(filtered)
        url = f"{self._base_url}{path}{query}"
        headers = self._auth_headers()
        payload = self._request_json(
            "GET",
            path,
            url=url,
            headers=headers,
            body=None,
            params=request_params,
            timeout=self._effective_timeout(timeout),
        )
        return self._unwrap_data(payload, method="GET", path=path, params=request_params)

    def post(
        self,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        timeout: float | None = None,
    ) -> Any:
        """发起 POST JSON 请求并返回 ``data`` 字段。

        Args:
            path: API 路径。
            body: JSON 请求体。
            timeout: 覆盖默认超时秒数。

        Returns:
            响应体中的 ``data``。

        Raises:
            TikHubApiError: 响应码非 200 或缺少 data。
        """
        url = f"{self._base_url}{path}"
        headers = self._auth_headers()
        headers["Content-Type"] = "application/json"
        request_body = body or {}
        encoded = json.dumps(request_body, ensure_ascii=False).encode("utf-8")
        payload = self._request_json(
            "POST",
            path,
            url=url,
            headers=headers,
            body=encoded,
            params=request_body,
            timeout=self._effective_timeout(timeout),
        )
        return self._unwrap_data(payload, method="POST", path=path, params=request_body)

    def _auth_headers(self) -> dict[str, str]:
        headers = dict(self._DEFAULT_HEADERS)
        headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _effective_timeout(self, timeout: float | None) -> float:
        return timeout if timeout is not None else self._timeout

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        url: str,
        headers: dict[str, str],
        body: bytes | None,
        params: dict[str, Any] | None,
        timeout: float,
    ) -> Any:
        self.request_log.append(
            TikHubApiCall(method=method, path=path, params=params),
        )
        try:
            if method == "GET":
                return get_json(url, timeout=timeout, headers=headers)
            return post_json(url, timeout=timeout, headers=headers, body=body or b"{}")
        except urllib.error.HTTPError as exc:
            response = read_http_error_payload(exc)
            detail = message_from_error_payload(response)
            if detail:
                message = f"TikHub 请求失败: {detail}"
            else:
                message = f"TikHub HTTP {exc.code}"
            raise TikHubApiError(
                message,
                method=method,
                path=path,
                params=params,
                http_status=exc.code,
                body=response,
            ) from exc

    def _unwrap_data(
        self,
        payload: Any,
        *,
        method: str,
        path: str,
        params: dict[str, Any] | None,
    ) -> Any:
        if not isinstance(payload, dict):
            raise TikHubApiError(
                "TikHub 响应不是 JSON 对象",
                method=method,
                path=path,
                params=params,
                body={"_raw": payload},
            )
        code = payload.get("code")
        if code not in (200, "200"):
            message = payload.get("message_zh") or payload.get("message") or str(code)
            raise TikHubApiError(
                f"TikHub 请求失败: {message}",
                method=method,
                path=path,
                params=params,
                body=payload,
            )
        if "data" not in payload:
            raise TikHubApiError(
                "TikHub 响应缺少 data 字段",
                method=method,
                path=path,
                params=params,
                body=payload,
            )
        return payload["data"]
