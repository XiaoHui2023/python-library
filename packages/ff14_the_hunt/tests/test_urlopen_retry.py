import ssl
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from ff14_the_hunt.common.urlopen_retry import (
    is_retryable_urlopen_error,
    retry_after_seconds_from_headers,
    urlopen_read,
)


def test_is_retryable_urlopen_error_for_ssl_eof() -> None:
    ssl_exc = ssl.SSLEOFError("EOF occurred in violation of protocol")
    url_error = urllib.error.URLError(ssl_exc)
    assert is_retryable_urlopen_error(url_error) is True


def test_is_retryable_urlopen_error_for_http_404() -> None:
    http_error = urllib.error.HTTPError(
        url="https://example.test",
        code=404,
        msg="Not Found",
        hdrs=None,
        fp=None,
    )
    assert is_retryable_urlopen_error(http_error) is False


def test_urlopen_read_retries_transient_failure() -> None:
    request = MagicMock()
    response = MagicMock()
    response.read.return_value = b"ok"
    response.__enter__.return_value = response
    response.__exit__.return_value = False

    ssl_exc = ssl.SSLEOFError("EOF occurred in violation of protocol")
    url_error = urllib.error.URLError(ssl_exc)

    with patch("ff14_the_hunt.common.urlopen_retry.time.sleep"):
        with patch(
            "ff14_the_hunt.common.urlopen_retry.urllib.request.urlopen",
            side_effect=[url_error, response],
        ) as mock_urlopen:
            raw = urlopen_read(request, timeout=5.0, max_attempts=3)

    assert raw == b"ok"
    assert mock_urlopen.call_count == 2


def test_retry_after_seconds_from_headers_delta_seconds() -> None:
    assert retry_after_seconds_from_headers({"Retry-After": "12"}) == 12.0


def test_urlopen_read_respects_retry_after_header() -> None:
    request = MagicMock()
    response = MagicMock()
    response.read.return_value = b"ok"
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    http_error = urllib.error.HTTPError(
        url="https://example.test",
        code=429,
        msg="Too Many Requests",
        hdrs={"Retry-After": "7"},
        fp=None,
    )
    sleep = MagicMock()

    with patch(
        "ff14_the_hunt.common.urlopen_retry.urllib.request.urlopen",
        side_effect=[http_error, response],
    ):
        raw = urlopen_read(
            request,
            timeout=5.0,
            max_attempts=2,
            jitter_ratio=0.0,
            sleep=sleep,
        )

    assert raw == b"ok"
    sleep.assert_called_once_with(7.0)


def test_urlopen_read_raises_after_exhausted_retries() -> None:
    request = MagicMock()
    ssl_exc = ssl.SSLEOFError("EOF occurred in violation of protocol")
    url_error = urllib.error.URLError(ssl_exc)

    with patch("ff14_the_hunt.common.urlopen_retry.time.sleep"):
        with patch(
            "ff14_the_hunt.common.urlopen_retry.urllib.request.urlopen",
            side_effect=url_error,
        ):
            with pytest.raises(urllib.error.URLError):
                urlopen_read(request, timeout=5.0, max_attempts=2)
