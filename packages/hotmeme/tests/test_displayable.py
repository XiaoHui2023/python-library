from hotmeme.filter.displayable import filter_displayable_media, has_displayable_media
from hotmeme.models import ImageItem, MediaType


def _item(**kwargs: object) -> ImageItem:
    base = {
        "id": "x:1",
        "provider": "tikhub",
        "source_id": "1",
        "title": "t",
        "image_url": "",
        "source_url": "https://example.com/post",
        "media_type": MediaType.IMAGE,
    }
    base.update(kwargs)
    return ImageItem.model_validate(base)


def test_video_requires_video_url() -> None:
    assert has_displayable_media(
        _item(media_type=MediaType.VIDEO, video_url="https://v.example/a.mp4"),
    )
    assert not has_displayable_media(_item(media_type=MediaType.VIDEO))


def test_image_requires_image_url() -> None:
    assert has_displayable_media(
        _item(media_type=MediaType.IMAGE, image_url="https://img.example/a.jpg"),
    )
    assert not has_displayable_media(_item(media_type=MediaType.IMAGE))


def test_filter_drops_text_only() -> None:
    items = [
        _item(media_type=MediaType.IMAGE, image_url="https://img.example/a.jpg"),
        _item(media_type=MediaType.IMAGE),
        _item(media_type=MediaType.VIDEO, video_url="https://v.example/b.mp4"),
    ]
    kept = filter_displayable_media(items)
    assert len(kept) == 2
