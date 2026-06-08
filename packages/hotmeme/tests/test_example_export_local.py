from pathlib import Path

from hotmeme.models import ImageBlob, ImageItem, MediaType
from hotmeme.renderer.models import MemeOutputPacket, OutputMediaKind
from hotmeme.renderer.render import render_item

from example.export_local import export_packet_images, extension_for, packet_json_view

_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 300


def _packet_with_blob() -> MemeOutputPacket:
    item = ImageItem(
        id="x:1",
        provider="tikhub",
        source_id="note-1",
        title="标题",
        image_urls=["https://example.com/1.jpg"],
        image_blobs=[ImageBlob(data=_JPEG, content_type="image/jpeg")],
        image_url="https://example.com/1.jpg",
        source_url="https://www.xiaohongshu.com/explore/1",
        community="xiaohongshu",
        media_type=MediaType.IMAGE,
    )
    return render_item(item)


def test_extension_for_jpeg() -> None:
    assert extension_for("image/jpeg") == ".jpg"


def test_export_packet_images_writes_files(tmp_path: Path) -> None:
    packet = _packet_with_blob()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    paths = export_packet_images(1, packet, run_dir, path_root=tmp_path)
    assert len(paths) == 1
    file_path = tmp_path / paths[0]
    assert file_path.is_file()
    assert file_path.read_bytes() == _JPEG


def test_packet_json_view_uses_local_path() -> None:
    packet = _packet_with_blob()
    view = packet_json_view(packet, ["output/run/001_note/image_01.jpg"])
    assert view["message"]["images"][0]["local_path"] == "output/run/001_note/image_01.jpg"
    assert view["message"]["text"] == "标题"
