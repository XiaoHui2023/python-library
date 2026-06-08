from hotmeme.models import ImageBlob, ImageItem, MediaType
from hotmeme.renderer.content import ContentBlockKind, build_post_content

_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 8
_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8


def test_build_post_content_orders_images_before_text() -> None:
    item = ImageItem(
        id="x:1",
        provider="tikhub",
        source_id="1",
        title="封面标题",
        body="正文说明",
        image_urls=[
            "https://example.com/1.jpg",
            "https://example.com/2.jpg",
        ],
        image_blobs=[
            ImageBlob(data=_JPEG, content_type="image/jpeg"),
            ImageBlob(data=_PNG, content_type="image/png"),
        ],
        image_url="https://example.com/1.jpg",
        source_url="https://www.xiaohongshu.com/explore/1",
        community="xiaohongshu",
        media_type=MediaType.IMAGE,
    )
    content = build_post_content(item, media_url=item.image_urls[0])
    kinds = [block.kind for block in content.blocks]
    assert kinds == [
        ContentBlockKind.IMAGE,
        ContentBlockKind.IMAGE,
        ContentBlockKind.TEXT,
    ]
    assert content.blocks[0].data == _JPEG
    assert content.blocks[1].content_type == "image/png"
    assert "封面标题" in content.blocks[2].text
    assert "正文说明" in content.blocks[2].text
