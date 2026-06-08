from unittest.mock import patch

import pytest

from hotmeme.assets.download import ImageDownloadError, download_image
from hotmeme.assets.materialize import materialize_image_items_traced
from hotmeme.models import AssetsPolicy, ImageBlob, ImageItem, MediaType

_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 300
_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 300


def _item(**kwargs) -> ImageItem:
    base = dict(
        id="tikhub:xhs:1",
        provider="tikhub",
        source_id="note1",
        title="标题",
        image_urls=["https://example.com/a.jpg"],
        image_url="https://example.com/a.jpg",
        source_url="https://www.xiaohongshu.com/explore/note1",
        community="xiaohongshu",
        media_type=MediaType.IMAGE,
    )
    base.update(kwargs)
    return ImageItem(**base)


def test_download_maps_read_timeout_to_error() -> None:
    class FakeResponse:
        status = 200
        headers = {"Content-Type": "image/jpeg"}

        def read(self) -> bytes:
            raise TimeoutError("The read operation timed out")

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

    with patch("urllib.request.urlopen", return_value=FakeResponse()):
        with pytest.raises(ImageDownloadError, match="读取超时"):
            download_image(
                "https://example.com/a.jpg",
                timeout=5.0,
                min_bytes=256,
            )


def test_download_rejects_small_payload() -> None:
    class FakeResponse:
        status = 200
        headers = {"Content-Type": "image/jpeg"}

        def read(self) -> bytes:
            return b"html"

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

    with patch("urllib.request.urlopen", return_value=FakeResponse()):
        with pytest.raises(ImageDownloadError, match="体积过小"):
            download_image(
                "https://example.com/a.jpg",
                timeout=5.0,
                min_bytes=256,
            )


def test_download_image_returns_blob() -> None:
    class FakeResponse:
        status = 200
        headers = {"Content-Type": "image/jpeg"}

        def read(self) -> bytes:
            return _JPEG

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

    with patch("urllib.request.urlopen", return_value=FakeResponse()):
        blob = download_image(
            "https://example.com/a.jpg",
            timeout=5.0,
            min_bytes=256,
        )
    assert blob.data.startswith(b"\xff\xd8\xff")
    assert blob.content_type == "image/jpeg"


def test_materialize_drops_item_when_download_fails() -> None:
    policy = AssetsPolicy(download=True, timeout=5.0)

    def fail_download(*args, **kwargs):
        raise ImageDownloadError("HTTP 403")

    with patch("hotmeme.assets.materialize.download_image", side_effect=fail_download):
        kept, errors, stage = materialize_image_items_traced([_item()], policy=policy)

    assert kept == []
    assert len(errors) == 1
    assert "下载失败" in errors[0]
    assert stage is not None
    assert stage.dropped == 1


def test_materialize_reports_progress() -> None:
    policy = AssetsPolicy(download=True, timeout=5.0)
    blob = ImageBlob(data=_PNG, content_type="image/png")
    messages: list[str] = []

    with patch("hotmeme.assets.materialize.download_image", return_value=blob):
        materialize_image_items_traced(
            [_item()],
            policy=policy,
            on_progress=messages.append,
        )

    assert any("待下载帖子" in msg for msg in messages)
    assert any("下载中" in msg for msg in messages)
    assert any("下载完成" in msg for msg in messages)


def test_materialize_caps_images_per_item() -> None:
    policy = AssetsPolicy(download=True, timeout=5.0, max_images_per_item=2)
    blob = ImageBlob(data=_PNG, content_type="image/png")
    item = _item(
        image_urls=[
            "https://example.com/1.jpg",
            "https://example.com/2.jpg",
            "https://example.com/3.jpg",
        ],
    )

    with patch("hotmeme.assets.materialize.download_image", return_value=blob) as mock_dl:
        kept, errors, _stage = materialize_image_items_traced([item], policy=policy)

    assert errors == []
    assert len(kept) == 1
    assert len(kept[0].image_blobs) == 2
    assert kept[0].image_urls == [
        "https://example.com/1.jpg",
        "https://example.com/2.jpg",
    ]
    assert mock_dl.call_count == 2


def test_materialize_parallel_preserves_image_order() -> None:
    policy = AssetsPolicy(download=True, timeout=5.0, download_workers=4)
    jpeg_blob = ImageBlob(data=_JPEG, content_type="image/jpeg")
    png_blob = ImageBlob(data=_PNG, content_type="image/png")
    item = _item(
        image_urls=[
            "https://example.com/1.jpg",
            "https://example.com/2.jpg",
        ],
    )

    def download_side_effect(url: str, **kwargs):
        if url.endswith("1.jpg"):
            return jpeg_blob
        return png_blob

    with patch(
        "hotmeme.assets.materialize.download_image",
        side_effect=download_side_effect,
    ):
        kept, errors, _stage = materialize_image_items_traced([item], policy=policy)

    assert errors == []
    assert kept[0].image_blobs == [jpeg_blob, png_blob]


def test_materialize_keeps_item_with_image_blobs() -> None:
    policy = AssetsPolicy(download=True, timeout=5.0)
    blob = ImageBlob(data=_PNG, content_type="image/png")

    with patch("hotmeme.assets.materialize.download_image", return_value=blob):
        kept, errors, stage = materialize_image_items_traced([_item()], policy=policy)

    assert errors == []
    assert len(kept) == 1
    assert kept[0].image_blobs == [blob]
    assert stage is not None
    assert stage.out_count == 1
