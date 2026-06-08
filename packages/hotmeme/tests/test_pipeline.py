from unittest.mock import patch

from hotmeme import HotMeme
from hotmeme.common.errors import TikHubApiError


def test_fetch_hot_posts_without_enabled_tikhub() -> None:
    client = HotMeme(tikhub_enabled=False)
    feed = client.fetch_hot_posts()
    assert feed.items == []
    assert feed.providers_ok == []
    assert feed.providers_failed == []
    assert feed.fetch_errors == []


@patch("hotmeme.pipeline.fetch_hot_posts.TikHubSource.fetch_hot_posts")
def test_fetch_hot_posts_records_platform_errors(mock_fetch) -> None:
    mock_fetch.side_effect = TikHubApiError("TikHub 请求失败: 邮箱未验证")
    client = HotMeme(api_key="test-key", platforms=["xiaohongshu", "douyin"])
    feed = client.fetch_hot_posts()
    assert feed.items == []
    assert feed.providers_failed == ["tikhub"]
    assert len(feed.fetch_errors) == 2
    assert all("邮箱未验证" in err for err in feed.fetch_errors)
    assert all(err.startswith("[xiaohongshu]") or err.startswith("[douyin]") for err in feed.fetch_errors)
