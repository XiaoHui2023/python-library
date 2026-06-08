from hotmeme.filter.risk import filter_risk_items
from hotmeme.models import ImageItem, MediaType


def test_risk_filter_blocks_sensitive_title() -> None:
    item = ImageItem(
        id="x:1",
        provider="tikhub",
        source_id="1",
        title="习近平相关标题",
        image_url="https://img.example/a.jpg",
        source_url="https://example.com/post",
        media_type=MediaType.IMAGE,
    )
    assert filter_risk_items([item]) == []
