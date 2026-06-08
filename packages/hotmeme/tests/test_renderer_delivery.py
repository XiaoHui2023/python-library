from hotmeme.models import ImageBlob, ImageItem, MediaType
from hotmeme.renderer.content import build_post_content
from hotmeme.renderer.delivery import message_from_packet
from hotmeme.renderer.render import render_item

_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 8
_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8


def _item_with_images(count: int) -> ImageItem:
    urls = [f"https://example.com/{index}.jpg" for index in range(1, count + 1)]
    blobs = [
        ImageBlob(data=_JPEG, content_type="image/jpeg"),
        ImageBlob(data=_PNG, content_type="image/png"),
        ImageBlob(data=_JPEG, content_type="image/jpeg"),
    ][:count]
    return ImageItem(
        id="x:1",
        provider="tikhub",
        source_id="1",
        title="标题",
        body="正文",
        image_urls=urls,
        image_blobs=blobs,
        image_url=urls[0],
        source_url="https://www.xiaohongshu.com/explore/1",
        community="xiaohongshu",
        media_type=MediaType.IMAGE,
    )


def test_build_post_content_respects_max_images() -> None:
    content = build_post_content(
        _item_with_images(3),
        media_url="https://example.com/1.jpg",
        max_images_per_item=2,
    )
    image_blocks = [block for block in content.blocks if block.kind.value == "image"]
    assert len(image_blocks) == 2


def test_message_from_packet_groups_images_and_text() -> None:
    packet = render_item(_item_with_images(2), max_images_per_item=2)
    message = message_from_packet(packet)
    assert len(message.images) == 2
    assert message.text is not None
    assert "正文" in message.text
    assert message.reference.source_url.endswith("/1")
