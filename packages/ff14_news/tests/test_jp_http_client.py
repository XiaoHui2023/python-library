from http.client import RemoteDisconnected

import pytest

from ff14_news.channels.jp_official import http_client


def test_fetch_html_wraps_network_error_with_request_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_urlopen_read(*args, **kwargs):
        raise RemoteDisconnected("Remote end closed connection without response")

    monkeypatch.setattr(http_client, "urlopen_read", fail_urlopen_read)

    with pytest.raises(RuntimeError) as exc_info:
        http_client.fetch_html(
            "https://jp.finalfantasyxiv.com/lodestone/topics/",
            timeout_seconds=120.0,
        )

    message = str(exc_info.value)
    assert "https://jp.finalfantasyxiv.com/lodestone/topics/" in message
    assert "timeout=120.0s" in message
    assert isinstance(exc_info.value.__cause__, RemoteDisconnected)
