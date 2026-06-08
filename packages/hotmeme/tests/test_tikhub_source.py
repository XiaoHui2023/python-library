from unittest.mock import MagicMock, patch

from hotmeme.models import TikHubConfig
from hotmeme.sources.platform_fetch import PlatformFetchResult
from hotmeme.sources.tikhub import TikHubSource


@patch("hotmeme.sources.tikhub.fetch_platform_hot_posts")
@patch("hotmeme.sources.tikhub.TikHubClient")
def test_tikhub_source_fetch(mock_client_cls, mock_fetch) -> None:
    mock_fetch.return_value = PlatformFetchResult()
    source = TikHubSource(TikHubConfig(api_key="test-key"))
    items = source.fetch_hot_posts(platform="xiaohongshu")
    assert items == []
    mock_client_cls.assert_called_once()
    mock_fetch.assert_called_once()
