from unittest.mock import patch

from hotmeme import HotMeme, crawl_once
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


@patch.object(HotMeme, "_fetch_round")
def test_crawl_once_function_one_shot(mock_fetch_round) -> None:
    mock_fetch_round.return_value = FetchedRound(
        items=[_sample_image("a")],
        providers_ok=["tikhub"],
    )
    packet = crawl_once(tikhub_enabled=False)
    assert len(packet.new_items) == 1
    assert packet.is_initial is True


@patch.object(HotMeme, "_fetch_round")
def test_crawl_once_function_reuses_client(mock_fetch_round) -> None:
    mock_fetch_round.return_value = FetchedRound(
        items=[_sample_image("a")],
        providers_ok=["tikhub"],
    )
    client = HotMeme(tikhub_enabled=False)
    first = crawl_once(client=client)
    mock_fetch_round.return_value = FetchedRound(
        items=[_sample_image("a"), _sample_image("b")],
        providers_ok=["tikhub"],
    )
    second = crawl_once(client=client)
    assert first.is_initial is True
    assert second.is_initial is False
    assert [item.id for item in second.new_items] == ["b"]
