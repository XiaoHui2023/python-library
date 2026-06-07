from ff14_news.channels.cn_weibo.mblog_parser import (
    blocks_from_mblog,
    effective_mblog,
    mblog_to_article,
    mblog_to_list_item,
    needs_detail_fetch,
)
from ff14_news.models import NewsBlockType

MBLOG_FIXTURE: dict = {
    "id": "5123456789012345",
    "mid": "5123456789012345",
    "created_at": "Wed Jun 04 10:00:00 +0800 2025",
    "text": (
        "《最终幻想14》7.51版本更新笔记公开<br />"
        "详细内容请见官网。"
    ),
    "pics": [
        {
            "large": {"url": "https://wx1.sinaimg.cn/large/example.jpg"},
        }
    ],
}

RETWEET_FIXTURE: dict = {
    "id": "5999888777666555",
    "created_at": "Wed Jun 04 11:00:00 +0800 2025",
    "text": "转发微博",
    "retweeted_status": {
        "id": "5111222333444555",
        "text": "内层原博标题<br />原博正文",
        "pics": [],
    },
}

LONG_TEXT_FIXTURE: dict = {
    "id": "5000111222333444",
    "created_at": "Wed Jun 04 12:00:00 +0800 2025",
    "text": "摘要内容……<a href=\"/status/5000111222333444\">全文</a>",
    "isLongText": True,
}


def test_effective_mblog_uses_inner_for_retweet() -> None:
    inner = effective_mblog(RETWEET_FIXTURE)
    assert inner["id"] == "5111222333444555"
    assert "原博正文" in inner["text"]


def test_needs_detail_fetch_detects_long_text() -> None:
    assert needs_detail_fetch(LONG_TEXT_FIXTURE) is True
    assert needs_detail_fetch(MBLOG_FIXTURE) is False


def test_mblog_to_list_item_reads_id_and_title() -> None:
    item = mblog_to_list_item(MBLOG_FIXTURE, channel_id="cn_weibo")
    assert item.id == "5123456789012345"
    assert item.channel_id == "cn_weibo"
    assert "7.51" in item.title
    assert item.cover_image_url == "https://wx1.sinaimg.cn/large/example.jpg"


def test_mblog_to_article_builds_blocks() -> None:
    article = mblog_to_article(MBLOG_FIXTURE, channel_id="cn_weibo")
    assert article.id == "5123456789012345"
    assert any(
        block.type == NewsBlockType.TEXT and block.text and "7.51" in block.text
        for block in article.blocks
    )
    assert any(
        block.type == NewsBlockType.IMAGE
        and block.url == "https://wx1.sinaimg.cn/large/example.jpg"
        for block in article.blocks
    )


def test_blocks_from_mblog_retweet_uses_inner_text() -> None:
    blocks = blocks_from_mblog(RETWEET_FIXTURE)
    assert any(block.text and "原博正文" in block.text for block in blocks)
