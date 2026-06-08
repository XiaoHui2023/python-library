from hotmeme.filter.media_type import filter_media_types
from hotmeme.models import ImageItem, MediaType


def _item(media_type: MediaType) -> ImageItem:
    return ImageItem(
        id=f"id:{media_type.value}",
        provider="tikhub",
        source_id=media_type.value,
        title=media_type.value,
        image_url="https://example.com/a.jpg",
        source_url="https://www.xiaohongshu.com/explore/1",
        community="xiaohongshu",
        media_type=media_type,
        video_url="https://example.com/v.mp4" if media_type == MediaType.VIDEO else None,
    )


def test_filter_media_types_keeps_images_only() -> None:
    items = [
        _item(MediaType.IMAGE),
        _item(MediaType.VIDEO),
        _item(MediaType.GIF),
    ]
    kept = filter_media_types(
        items,
        allowed=[MediaType.IMAGE, MediaType.GIF],
    )
    assert [item.media_type for item in kept] == [MediaType.IMAGE, MediaType.GIF]
