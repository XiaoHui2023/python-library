from ff14_news.channels.cn_official.html_content import html_to_blocks
from ff14_news.models import NewsBlockType


def test_html_to_blocks_strips_style_and_keeps_order() -> None:
    html = """
    <style>.x{color:red}</style>
    <div class="newcontbox">
      <p>第一段</p>
      <img src="//fu5.web.sdo.com/a.jpg" alt="图注">
      <h2>小标题</h2>
      <p>第二段</p>
    </div>
    <p>分享到：</p>
    """
    blocks = html_to_blocks(html)
    types = [b.type for b in blocks]
    assert types[0] == NewsBlockType.TEXT
    assert blocks[0].text == "第一段"
    assert types[1] == NewsBlockType.IMAGE
    assert blocks[1].url == "https://fu5.web.sdo.com/a.jpg"
    assert types[2] == NewsBlockType.HEADING
    assert blocks[2].text == "小标题"
    assert blocks[-1].text == "第二段"
    assert all(b.text != "分享到：" for b in blocks if b.text)
