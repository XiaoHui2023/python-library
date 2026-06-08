from hotmeme import render_item, render_items
from hotmeme.models import ImageBlob, ImageItem, MediaType
from hotmeme.renderer.content import ContentBlockKind, compose_post_text

_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 8


def _image_item(*, video_url: str | None = None, body: str | None = None) -> ImageItem:
    return ImageItem(
        id="tikhub:abc",
        provider="tikhub",
        source_id="abc",
        title="标题",
        body=body,
        image_urls=["https://example.com/i.jpg"],
        image_blobs=[ImageBlob(data=_JPEG, content_type="image/jpeg")],
        image_url="https://example.com/i.jpg",
        video_url=video_url,
        source_url="https://example.com/p",
        author="作者",
        community="xiaohongshu",
        media_type=MediaType.VIDEO if video_url else MediaType.IMAGE,
    )


def test_render_image_packet_content_blocks() -> None:
    packet = render_item(_image_item(body="正文第二段"))
    assert packet.media_kind.value == "image"
    assert packet.media_url == "https://example.com/i.jpg"
    assert len(packet.content.blocks) == 2
    assert packet.content.blocks[0].kind == ContentBlockKind.IMAGE
    assert packet.content.blocks[0].data == _JPEG
    assert packet.content.blocks[0].content_type == "image/jpeg"
    assert packet.content.blocks[1].kind == ContentBlockKind.TEXT
    assert "标题" in packet.content.blocks[1].text
    assert "正文第二段" in packet.content.blocks[1].text
    assert "作者" not in packet.content.blocks[1].text
    assert packet.reference.author == "作者"
    assert packet.reference.source_url == "https://example.com/p"
    assert packet.reference.image_source_urls == ["https://example.com/i.jpg"]


def test_compose_post_text_merges_title_and_body() -> None:
    item = _image_item(body="标题\n\n更多正文")
    assert compose_post_text(item) == "标题\n\n更多正文"


def test_render_video_packet() -> None:
    packet = render_item(_image_item(video_url="https://example.com/v.mp4"))
    assert packet.media_kind.value == "video"
    assert packet.media_url == "https://example.com/v.mp4"
    assert packet.content.blocks[0].kind == ContentBlockKind.VIDEO


def test_render_video_prefers_openable_link_when_stream_expires() -> None:
    item = ImageItem(
        id="tikhub:dy",
        provider="tikhub",
        source_id="dy",
        title="视频",
        image_url="https://example.com/cover.jpg",
        video_url="https://v.douyinvod.com/v.mp4?Expires=1",
        preview_url="https://example.com/preview.jpg",
        source_url="https://www.douyin.com/video/1",
        community="douyin",
        media_type=MediaType.VIDEO,
    )
    packet = render_item(item)
    assert packet.media_url == "https://example.com/preview.jpg"
    assert packet.thumbnail_url == "https://example.com/cover.jpg"


def test_render_items_batch() -> None:
    batch = render_items([_image_item(), _image_item(video_url="https://example.com/v.mp4")])
    assert len(batch.packets) == 2
