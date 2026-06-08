from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from hotmeme.renderer.content import ContentBlockKind
from hotmeme.renderer.delivery import message_from_packet
from hotmeme.renderer.models import MemeOutputPacket

_MIME_EXT = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


def safe_dir_name(source_id: str) -> str:
    text = re.sub(r"[^\w\-.]+", "_", source_id.strip())
    return text[:64] or "post"


def extension_for(content_type: str | None) -> str:
    if content_type:
        ext = _MIME_EXT.get(content_type.lower())
        if ext:
            return ext
    return ".bin"


def make_run_dir(base: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = base / stamp
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def export_packet_images(
    index: int,
    packet: MemeOutputPacket,
    run_dir: Path,
    *,
    path_root: Path,
) -> list[str]:
    """把本条消息内的图片写入同一目录，返回按图序排列的本地路径。"""
    folder = run_dir / f"{index:03d}_{safe_dir_name(packet.source_id)}"
    folder.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    image_no = 0
    for block in packet.content.blocks:
        if block.kind != ContentBlockKind.IMAGE or not block.data:
            continue
        image_no += 1
        filename = f"image_{image_no:02d}{extension_for(block.content_type)}"
        file_path = folder / filename
        file_path.write_bytes(block.data)
        paths.append(str(file_path.relative_to(path_root)))
    return paths


def packet_json_view(
    packet: MemeOutputPacket,
    image_local_paths: list[str],
) -> dict:
    """JSON：一条 message（多图+正文）+ reference。"""
    message = message_from_packet(packet)
    images_payload = []
    path_index = 0
    for image in message.images:
        entry = {
            "content_type": image.content_type,
            "url": image.url,
        }
        if path_index < len(image_local_paths):
            entry["local_path"] = image_local_paths[path_index]
            path_index += 1
        images_payload.append(entry)
    return {
        "item_id": packet.item_id,
        "title": packet.title,
        "message": {
            "images": images_payload,
            "text": message.text,
        },
        "reference": message.reference.model_dump(mode="python"),
        "platform": packet.platform,
        "score": packet.score,
        "rank_score": packet.rank_score,
    }
