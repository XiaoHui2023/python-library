from __future__ import annotations

import ssl
import time
import urllib.error
import urllib.request

_RETRYABLE_HTTP_CODES = frozenset({408, 429, 500, 502, 503, 504})
_DEFAULT_MAX_ATTEMPTS = 4
_DEFAULT_INITIAL_BACKOFF_SECONDS = 1.0
_DEFAULT_MAX_BACKOFF_SECONDS = 8.0


def is_retryable_urlopen_error(exc: BaseException) -> bool:
    """判断 ``urlopen`` 相关异常是否宜短暂等待后重试。"""
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code in _RETRYABLE_HTTP_CODES
    if isinstance(exc, TimeoutError):
        return True
    if isinstance(exc, urllib.error.URLError):
        reason = exc.reason
        if isinstance(reason, TimeoutError):
            return True
        if isinstance(reason, (ssl.SSLError, ConnectionResetError, OSError)):
            return True
        return True
    if isinstance(exc, (ssl.SSLError, ConnectionResetError, OSError)):
        return True
    return False


def urlopen_read(
    request: urllib.request.Request,
    *,
    timeout: float,
    max_attempts: int = _DEFAULT_MAX_ATTEMPTS,
    initial_backoff_seconds: float = _DEFAULT_INITIAL_BACKOFF_SECONDS,
    max_backoff_seconds: float = _DEFAULT_MAX_BACKOFF_SECONDS,
) -> bytes:
    """``urlopen`` 读响应体；瞬时网络或 TLS 失败时指数退避重试。

    Args:
        request: 待发送请求。
        timeout: 单次 ``urlopen`` 超时秒数。
        max_attempts: 最多尝试次数（含首次）。
        initial_backoff_seconds: 首次重试前等待秒数。
        max_backoff_seconds: 退避等待上限秒数。

    Returns:
        响应体原始字节。

    Raises:
        urllib.error.HTTPError: 不可重试的 HTTP 状态，或重试耗尽后的 HTTP 错误。
        urllib.error.URLError: 重试耗尽后的网络或 TLS 错误。
        TimeoutError: 重试耗尽后的超时。
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    last_exc: BaseException | None = None
    backoff = initial_backoff_seconds
    for attempt in range(max_attempts):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except BaseException as exc:
            last_exc = exc
            if attempt + 1 >= max_attempts or not is_retryable_urlopen_error(exc):
                raise
            time.sleep(min(backoff, max_backoff_seconds))
            backoff = min(backoff * 2.0, max_backoff_seconds)

    if last_exc is not None:
        raise last_exc
    raise RuntimeError("urlopen_read ended without response or error")
