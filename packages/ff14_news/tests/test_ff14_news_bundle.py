from datetime import datetime, timezone
from http.client import RemoteDisconnected
from unittest.mock import MagicMock

import pytest

from ff14_news import FF14News
from ff14_news.models import NewsArticle, NewsFeed


def _sample_feed(channel_id: str) -> NewsFeed:
    article = NewsArticle(
        channel_id=channel_id,
        id="1",
        title=f"{channel_id} title",
        publish_date=datetime(2026, 6, 8, tzinfo=timezone.utc),
        summary="summary",
        source_page_url=f"https://example.test/{channel_id}/1",
    )
    return NewsFeed(
        channel_id=channel_id,
        source_list_url=f"https://example.test/{channel_id}",
        fetched_at=datetime(2026, 6, 8, tzinfo=timezone.utc),
        articles=[article],
    )


def test_available_channels_respects_enable_flags() -> None:
    news = FF14News(
        enable_cn_official=True,
        enable_cn_weibo=False,
        enable_jp_official=False,
    )
    assert news.available_channels() == ["cn_official"]


def test_disabled_channel_raises() -> None:
    news = FF14News(enable_cn_weibo=False)
    with pytest.raises(KeyError, match="disabled"):
        news.cn_weibo


def test_fetch_articles_requires_enabled_channel() -> None:
    news = FF14News(
        enable_cn_official=False,
        enable_cn_weibo=False,
        enable_jp_official=False,
    )
    with pytest.raises(ValueError, match="no channels enabled"):
        news.fetch_articles()


def test_fetch_articles_parallel_bundle(monkeypatch: pytest.MonkeyPatch) -> None:
    news = FF14News(
        enable_cn_official=True,
        enable_cn_weibo=False,
        enable_jp_official=True,
    )
    official = MagicMock()
    official.fetch_articles.return_value = _sample_feed("cn_official")
    jp = MagicMock()
    jp.fetch_articles.return_value = _sample_feed("jp_official")
    monkeypatch.setattr(news, "_channels", {
        "cn_official": official,
        "jp_official": jp,
    })

    bundle = news.fetch_articles(limit=1)

    assert set(bundle.feeds) == {"cn_official", "jp_official"}
    assert bundle.errors == []
    official.fetch_articles.assert_called_once_with(limit=1, page_index=0)
    jp.fetch_articles.assert_called_once_with(limit=1, page_index=0)


def test_fetch_articles_collects_channel_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    news = FF14News(enable_cn_official=True, enable_cn_weibo=False, enable_jp_official=False)
    failing = MagicMock()
    failing.fetch_articles.side_effect = RuntimeError("network down")
    monkeypatch.setattr(news, "_channels", {"cn_official": failing})

    bundle = news.fetch_articles(limit=2)

    assert bundle.feeds == {}
    assert len(bundle.errors) == 1
    assert bundle.errors[0].channel_id == "cn_official"
    assert "network down" in bundle.errors[0].message


def test_fetch_articles_error_message_includes_exception_chain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    news = FF14News(enable_cn_official=True, enable_cn_weibo=False, enable_jp_official=False)
    failing = MagicMock()
    failing.fetch_articles.side_effect = RuntimeError(
        "failed to fetch HTML from https://example.test/topics/ (timeout=120.0s)"
    )
    failing.fetch_articles.side_effect.__cause__ = RemoteDisconnected(
        "Remote end closed connection without response"
    )
    monkeypatch.setattr(news, "_channels", {"cn_official": failing})

    bundle = news.fetch_articles(limit=2)

    message = bundle.errors[0].message
    assert "RuntimeError: failed to fetch HTML from https://example.test/topics/" in message
    assert "RemoteDisconnected: Remote end closed connection without response" in message
