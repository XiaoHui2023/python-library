import io
import json
import urllib.error
from unittest.mock import patch

import pytest

from hotmeme.common.errors import TikHubApiError
from hotmeme.common.http_json import http_error_detail_message
from hotmeme.sources.tikhub_client import TikHubClient


def test_http_error_detail_message_reads_tikhub_detail() -> None:
    body = json.dumps(
        {
            "detail": {
                "message_zh": "邮箱未验证",
                "message": "Email is not verified",
            },
        },
    ).encode()
    exc = urllib.error.HTTPError(
        url="https://api.tikhub.io/test",
        code=403,
        msg="Forbidden",
        hdrs=None,
        fp=io.BytesIO(body),
    )
    assert http_error_detail_message(exc) == "邮箱未验证"


def test_http_error_detail_message_reads_plain_text_body() -> None:
    exc = urllib.error.HTTPError(
        url="https://api.tikhub.io/test",
        code=403,
        msg="Forbidden",
        hdrs=None,
        fp=io.BytesIO(b"error code: 1010"),
    )
    assert http_error_detail_message(exc) == "error code: 1010"


@patch("hotmeme.sources.tikhub_client.get_json")
def test_tikhub_client_raises_readable_http_error(mock_get_json) -> None:
    body = json.dumps(
        {
            "detail": {
                "message_zh": "邮箱未验证",
            },
        },
    ).encode()
    mock_get_json.side_effect = urllib.error.HTTPError(
        url="https://api.tikhub.io/test",
        code=403,
        msg="Forbidden",
        hdrs=None,
        fp=io.BytesIO(body),
    )
    client = TikHubClient(api_key="test-key")
    with pytest.raises(TikHubApiError, match="邮箱未验证") as raised:
        client.get("/api/v1/test")
    assert raised.value.body is not None
    assert raised.value.path == "/api/v1/test"
