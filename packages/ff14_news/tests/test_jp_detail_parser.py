from ff14_news.channels.jp_official.detail_parser import (
    parse_detail_metadata,
    parse_detail_page,
)


def test_parse_detail_page_extracts_wrapper() -> None:
    html = """
    <article class="news__detail">
    <header class="news__header">
    <script>ldst_strftime(1780574400, 'YMDHM');</script>
    <h1>見出しテスト</h1>
    </header>
    <div class="news__detail__wrapper">
    <img src="https://img.finalfantasyxiv.com/t/a.jpg">
    <p>本文テスト</p>
    </div>
    <div class="news__detail__social"></div>
    </article>
    """
    article = parse_detail_page(html, "abc123", channel_id="jp_official")
    assert article.title == "見出しテスト"
    assert article.id == "abc123"
    assert any(b.text and "本文" in b.text for b in article.blocks)


def test_parse_detail_metadata_has_no_blocks() -> None:
    html = """
    <article class="news__detail">
    <header class="news__header">
    <script>ldst_strftime(1780574400, 'YMDHM');</script>
    <h1>見出しテスト</h1>
    </header>
    <div class="news__detail__wrapper">
    <img src="https://img.finalfantasyxiv.com/t/a.jpg">
    <p>本文テスト</p>
    </div>
    <div class="news__detail__social"></div>
    </article>
    """
    article = parse_detail_metadata(html, "abc123", channel_id="jp_official")
    assert article.title == "見出しテスト"
    assert article.blocks == []
    assert "本文" in article.summary
