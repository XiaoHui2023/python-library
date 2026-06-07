from datetime import UTC, datetime
from unittest.mock import patch

from hotmeme import HotMeme
from hotmeme.cn_models import TopicItem
from hotmeme.crawl.round import FetchedRound
from hotmeme.models import ImageItem, MediaType


def _sample_image(item_id: str) -> ImageItem:
    return ImageItem(
        id=item_id,
        provider="tikhub",
        source_id=item_id,
        title="t",
        image_url="https://example.com/i.png",
        source_url="https://example.com/p",
        media_type=MediaType.IMAGE,
    )


def _sample_topic(topic_id: str) -> TopicItem:
    return TopicItem(
        id=topic_id,
        provider="hotpush",
        platform="weibo",
        title="hot",
        source_url="https://example.com/t",
        rank=1,
        timestamp=datetime.now(UTC),
    )


def test_hotmeme_instantiates() -> None:
    assert HotMeme() is not None


@patch.object(HotMeme, "_fetch_round")
def test_crawl_once_initial_and_delta(mock_fetch_round) -> None:
    mock_fetch_round.return_value = FetchedRound(
        items=[_sample_image("a"), _sample_image("b")],
        topics=[_sample_topic("t1")],
        providers_ok=["hotpush", "tikhub"],
    )
    client = HotMeme()
    first = client.crawl_once()
    assert first.is_initial is True
    assert len(first.new_items) == 2
    assert len(first.new_topics) == 1

    mock_fetch_round.return_value = FetchedRound(
        items=[_sample_image("b"), _sample_image("c")],
        topics=[_sample_topic("t1"), _sample_topic("t2")],
        providers_ok=["hotpush", "tikhub"],
    )
    second = client.crawl_once()
    assert second.is_initial is False
    assert [item.id for item in second.new_items] == ["c"]
    assert [topic.id for topic in second.new_topics] == ["t2"]


@patch.object(HotMeme, "_fetch_round")
def test_reset_seen(mock_fetch_round) -> None:
    mock_fetch_round.return_value = FetchedRound(
        items=[_sample_image("a")],
        providers_ok=["tikhub"],
    )
    client = HotMeme()
    client.crawl_once()
    client.reset_seen()
    second = client.crawl_once()
    assert second.is_initial is True
    assert len(second.new_items) == 1
