from hotmeme import render_item, render_items

from hotmeme.models import ImageItem, MediaType





def _image_item(*, video_url: str | None = None) -> ImageItem:

    return ImageItem(

        id="tikhub:abc",

        provider="tikhub",

        source_id="abc",

        title="标题",

        image_url="https://example.com/i.jpg",

        video_url=video_url,

        source_url="https://example.com/p",

        author="作者",

        community="xiaohongshu",

        media_type=MediaType.VIDEO if video_url else MediaType.IMAGE,

    )





def test_render_image_packet() -> None:

    packet = render_item(_image_item())

    assert packet.media_kind.value == "image"

    assert packet.media_url == "https://example.com/i.jpg"

    assert "作者" in packet.caption





def test_render_video_packet() -> None:

    packet = render_item(_image_item(video_url="https://example.com/v.mp4"))

    assert packet.media_kind.value == "video"

    assert packet.media_url == "https://example.com/v.mp4"





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

