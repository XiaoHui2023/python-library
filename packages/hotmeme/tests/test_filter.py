from hotmeme.filter.dedup import dedup_items, normalize_image_url
from hotmeme.filter.nsfw import filter_nsfw_items
from hotmeme.models import ImageItem, MediaType


def _item(**kwargs: object) -> ImageItem:
    base = {
        "id": "x:1",
        "provider": "tikhub",
        "source_id": "1",
        "title": "t",
        "image_url": "https://example.com/a.jpg",
        "source_url": "https://example.com/post",
        "media_type": MediaType.IMAGE,
        "nsfw": False,
    }
    base.update(kwargs)
    return ImageItem.model_validate(base)


def test_normalize_url_strips_fragment() -> None:
    a = normalize_image_url("https://Example.com/pic.jpg?b=2&a=1#frag")
    b = normalize_image_url("https://example.com/pic.jpg?a=1&b=2")
    assert a == b


def test_dedup_by_url() -> None:
    items = [
        _item(image_url="https://ex.com/a.jpg"),
        _item(image_url="https://ex.com/a.jpg?x=1", id="x:2"),
    ]
    assert len(dedup_items(items)) == 1


def test_nsfw_filter_blocks_flagged() -> None:
    items = [_item(nsfw=True)]
    assert filter_nsfw_items(items, allow_nsfw=False) == []
