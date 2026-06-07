from __future__ import annotations

import hashlib


def make_item_id(*, provider: str, source_id: str, image_url: str) -> str:
    """由来源与资源键生成库内稳定 ID。"""
    raw = f"{provider}\0{source_id}\0{image_url}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"{provider}:{digest}"
