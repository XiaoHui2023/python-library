import os

import pytest

from ff14_news import FF14News


@pytest.mark.skipif(
    os.environ.get("FF14_NEWS_INTEGRATION") != "1",
    reason="set FF14_NEWS_INTEGRATION=1 to hit live API",
)
def test_cn_official_fetch_latest_two() -> None:
    feed = FF14News().cn_official.fetch_articles(limit=2)
    assert feed.channel_id == "cn_official"
    assert len(feed.articles) == 2
    first = feed.articles[0]
    assert first.channel_id == "cn_official"
    assert int(first.id) > 0
    assert first.title
    assert first.blocks == []
