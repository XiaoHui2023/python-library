from ff14_news.channels.jp_official.list_parser import parse_topics_list_page


def test_parse_topics_list_page_reads_header_and_id() -> None:
    html = """
    <ul>
    <li class="news__list--topics ic__topics--list">
    <header class="news__list--header clearfix">
    <p class="news__list--title"><a href="/lodestone/topics/detail/abc123def456/">テストタイトル</a></p>
    <time class="news__list--time">
    <script>ldst_strftime(1780574400, 'YMD');</script>
    </time></header>
    <div class="news__list--banner">
    <a href="/lodestone/topics/detail/abc123def456/" class="news__list--img">
    <img src="https://img.finalfantasyxiv.com/t/abc.jpg" width="570" alt="">
    </a>
    <p class="mdl-text__xs-m16">バナー要約テキストです。</p>
    </div></li>
    </ul>
    """
    rows = parse_topics_list_page(html, limit=5)
    assert len(rows) == 1
    assert rows[0].article_id == "abc123def456"
    assert rows[0].title == "テストタイトル"
    assert rows[0].cover_image_url == "https://img.finalfantasyxiv.com/t/abc.jpg"
    assert "バナー要約" in rows[0].summary
