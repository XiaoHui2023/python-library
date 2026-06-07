from html.parser import HTMLParser
from urllib.parse import urljoin

from ff14_news.models import NewsBlockType, NewsContentBlock

_BLOCK_TAGS = frozenset(
    {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr", "img", "br"}
)
_SKIP_TAGS = frozenset({"style", "script", "head", "meta", "link", "noscript"})
_HEADING_LEVEL = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}


class _ContentHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[NewsContentBlock] = []
        self._skip_depth = 0
        self._text_buf: list[str] = []
        self._stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        self._stack.append(tag)
        if tag == "img":
            src = _attr(attrs, "src")
            if src:
                self._flush_text()
                self.blocks.append(
                    NewsContentBlock(
                        type=NewsBlockType.IMAGE,
                        url=src,
                        text=_attr(attrs, "alt"),
                    )
                )
            return
        if tag == "br":
            self._text_buf.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if self._stack and self._stack[-1] == tag:
            self._stack.pop()
        if tag in _HEADING_LEVEL:
            self._emit_text_block(NewsBlockType.HEADING, _HEADING_LEVEL[tag])
            return
        if tag == "p" or tag == "li":
            self._emit_text_block(NewsBlockType.TEXT, None)
            return
        if tag == "tr":
            self._emit_text_block(NewsBlockType.TEXT, None, join_cells=True)
            return

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._stack and self._stack[-1] == "img":
            return
        stripped = data.replace("\xa0", " ")
        if stripped.strip():
            self._text_buf.append(stripped)

    def close(self) -> None:
        super().close()
        if not self._skip_depth:
            self._flush_text()

    def _emit_text_block(
        self,
        block_type: NewsBlockType,
        level: int | None,
        *,
        join_cells: bool = False,
    ) -> None:
        text = "".join(self._text_buf).strip()
        self._text_buf.clear()
        if not text:
            return
        if join_cells:
            text = " | ".join(part.strip() for part in text.split("\n") if part.strip())
        self.blocks.append(
            NewsContentBlock(type=block_type, text=text, level=level)
        )

    def _flush_text(self) -> None:
        self._emit_text_block(NewsBlockType.TEXT, None)


def html_to_blocks(
    html: str,
    *,
    base_url: str,
    extra_boilerplate: frozenset[str] | None = None,
) -> list[NewsContentBlock]:
    """将 HTML 片段转为有序正文块。"""
    parser = _ContentHTMLParser()
    parser.feed(html or "")
    parser.close()
    return _normalize_blocks(
        parser.blocks,
        base_url=base_url,
        extra_boilerplate=extra_boilerplate,
    )


def _normalize_blocks(
    blocks: list[NewsContentBlock],
    *,
    base_url: str,
    extra_boilerplate: frozenset[str] | None,
) -> list[NewsContentBlock]:
    out: list[NewsContentBlock] = []
    for block in blocks:
        if block.type == NewsBlockType.IMAGE and block.url:
            url = block.url.strip()
            if not url.startswith(("http://", "https://")):
                url = urljoin(base_url, url)
            alt = (block.text or "").strip() or None
            out.append(
                NewsContentBlock(type=NewsBlockType.IMAGE, url=url, text=alt)
            )
            continue
        text = (block.text or "").strip()
        if not text:
            continue
        if block.type == NewsBlockType.TEXT and _is_boilerplate(
            text, extra_boilerplate
        ):
            continue
        out.append(
            NewsContentBlock(
                type=block.type,
                text=text,
                level=block.level,
                url=block.url,
            )
        )
    return _merge_adjacent_text(out)


def _merge_adjacent_text(blocks: list[NewsContentBlock]) -> list[NewsContentBlock]:
    merged: list[NewsContentBlock] = []
    for block in blocks:
        if (
            merged
            and block.type == NewsBlockType.TEXT
            and merged[-1].type == NewsBlockType.TEXT
        ):
            prev = merged[-1]
            merged[-1] = NewsContentBlock(
                type=NewsBlockType.TEXT,
                text=f"{prev.text}\n{block.text}",
            )
            continue
        merged.append(block)
    return merged


def _is_boilerplate(text: str, extra: frozenset[str] | None) -> bool:
    lowered = text.lower()
    if lowered in {"分享到：", "分享到:"}:
        return True
    if "copyright" in lowered and "square enix" in lowered:
        return True
    if extra and text.strip() in extra:
        return True
    return False


def _attr(attrs: list[tuple[str, str | None]], name: str) -> str | None:
    for key, value in attrs:
        if key.lower() == name and value:
            return value.strip()
    return None
