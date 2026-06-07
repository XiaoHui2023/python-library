from ff14_news.channels.cn_weibo.proxy_url import normalize_proxy_url


def test_normalize_proxy_url_adds_http_scheme() -> None:
    assert normalize_proxy_url("127.0.0.1:7897") == "http://127.0.0.1:7897"


def test_normalize_proxy_url_keeps_existing_scheme() -> None:
    assert normalize_proxy_url("http://127.0.0.1:7897") == "http://127.0.0.1:7897"


def test_normalize_proxy_url_empty() -> None:
    assert normalize_proxy_url("") is None
    assert normalize_proxy_url(None) is None
