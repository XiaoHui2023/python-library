from unittest.mock import patch

from hotmeme import HotMeme
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


def test_hotmeme_instantiates() -> None:
    assert HotMeme() is not None


@patch.object(HotMeme, "_fetch_round")
def test_crawl_once_initial_and_delta(mock_fetch_round) -> None:
    mock_fetch_round.return_value = FetchedRound(
        items=[_sample_image("a"), _sample_image("b")],
        providers_ok=["tikhub"],
    )
    client = HotMeme()
    first = client.crawl_once()
    assert first.is_initial is True
    assert len(first.new_items) == 2

    mock_fetch_round.return_value = FetchedRound(
        items=[_sample_image("b"), _sample_image("c")],
        providers_ok=["tikhub"],
    )
    second = client.crawl_once()
    assert second.is_initial is False
    assert [item.id for item in second.new_items] == ["c"]


@patch("hotmeme.hotmeme.materialize_image_items_traced")
@patch.object(HotMeme, "_fetch_round")
def test_render_output_materializes_after_fetch(
    mock_fetch_round,
    mock_materialize,
) -> None:
    item = _sample_image("a")
    mock_fetch_round.return_value = FetchedRound(
        items=[item],
        providers_ok=["tikhub"],
    )
    mock_materialize.return_value = ([item], [], None)
    client = HotMeme()
    packet = client.crawl_once()
    client.render_output(packet.fetched_items)
    mock_materialize.assert_called_once()


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
