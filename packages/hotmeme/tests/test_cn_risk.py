from hotmeme.filter.risk import filter_cn_risk_items
from hotmeme.models import ImageItem, MediaType


def _item(title: str) -> ImageItem:
    return ImageItem(
        id="cn:1",
        provider="weibo",
        source_id="1",
        title=title,
        image_url="https://img.example/a.jpg",
        source_url="https://weibo.com/1",
        media_type=MediaType.IMAGE,
    )


def test_cn_risk_blocks_ad_title() -> None:
    items = [_item("免费领取加微信")]
    assert filter_cn_risk_items(items) == []
