# python-library-ff14-news

多渠道 FF14 新闻抓取；各渠道代码分目录实现，输出统一的 `NewsFeed` / `NewsArticle`。

## 设计特性

### 渠道

| 标识 | 目录 | 说明 |
| --- | --- | --- |
| `cn_official` | `ff14_news/channels/cn_official/` | [国服官网](https://ff.web.sdo.com/web8/index.html#/newstab/newslist)，cqnews JSON（与 SPA 同源，非 Selenium） |
| `cn_weibo` | `ff14_news/channels/cn_weibo/` | [FF14 官方微博](https://weibo.com/cnff14)，m.weibo.cn 时间线 |
| `jp_official` | `ff14_news/channels/jp_official/` | [日文 Lodestone トピックス](https://jp.finalfantasyxiv.com/lodestone/topics/)，列表 `news__list--*` |

新渠道在 `ff14_news/channels/<id>/` 下单独实现，并在门面 `FF14News` 上挂同名属性。

### 返回结构

- `NewsFeed`：单渠道一次抓取；`channel_id`、列表 URL、`articles`（顺序与对应站点列表一致）。
- `NewsFeedBundle`：门面 `fetch_articles` 并行抓取已启用渠道；`feeds` 按 `channel_id` 索引，失败记入 `errors`。
- `NewsArticle`：列表级字段（`channel_id`、标题、摘要、头图、`source_page_url`）；默认 `blocks` 为空。
- 正文块：调用各渠道 `fetch_article_detail`（`fetch_article` 为别名）后 `blocks` 才有内容。

### 渠道开关

构造 `FF14News` 时用 `enable_cn_official` / `enable_cn_weibo` / `enable_jp_official`（默认均为 `True`）。未启用的渠道不构造实例，访问属性或 `channel(id)` 会 `KeyError`。

### 国服官网（cn_official）

- 列表栏目 `CategoryCode=5310`；详情页链接 `newscont/{id}`。
- `fetch_articles` / `fetch_articles_by_ids`：列表或详情 JSON 的标题、摘要、头图，不解析 HTML 正文。
- `fetch_article_detail`：详情 `Content` 转有序 `NewsContentBlock`。

### 日文官网（jp_official）

- 列表：`news__list--header`（标题/时间）、`news__list--banner`（摘要，纯文本最多 200 字）、`news__list--img`。
- `fetch_articles`：仅列表；`fetch_articles_by_ids`：先扫列表，未命中再拉详情元数据（无 blocks）。
- `fetch_article_detail`：详情页 `news__detail__wrapper` 全文块。
- 文章 `id` 为 Lodestone 十六进制串（非数字）。

### 官方微博（cn_weibo）

- 官方微博显示名「最终幻想14」、`@cnff14`（uid `1797798792`）；列表仅保留原发，跳过转发。
- 反爬：依赖 [crawl4weibo](https://pypi.org/project/crawl4weibo/) + **Playwright Chromium**（`example.bat` 首次运行会安装内核并取 Cookie）。
- 默认无 Cookie 时由 Playwright 打开移动端页获取会话；也可手动配置 `cn_weibo_cookie` 或 `example/weibo_cookie.txt`。
- 列表级 `summary` 恒为空；正文预览见 `title`（首行，最多 80 字）。
- `fetch_articles`：时间线列表级字段，不拉长文展开。
- `fetch_articles_by_ids`：时间线查找或单条元数据，无 blocks。
- `fetch_article_detail`：完整正文（含长文展开）。
- 文章 `id` 为微博 mblog id 字符串。

## 配置

| 项 | 说明 |
| --- | --- |
| `FF14News(enable_cn_official=…)` 等 | 构造时开关各渠道（默认全开） |
| `FF14News().cn_official.category_code` | 列表栏目，默认 `5310` |
| `FF14News(cn_official_timeout_seconds=…)` | 国服渠道 HTTP 超时 |
| `FF14News(cn_weibo_timeout_seconds=…)` | 微博渠道 HTTP 超时（默认 60s） |
| `FF14News(cn_weibo_cookie=…)` | 微博 Cookie 整串（跳过 Playwright 取 Cookie） |
| `FF14News(cn_weibo_cookie_storage_path=…)` | Playwright 会话缓存路径 |
| `FF14News(cn_weibo_browser_headless=…)` | 自动取 Cookie 时是否无头浏览器（默认 True） |
| `FF14News(jp_official_timeout_seconds=…)` | 日文渠道 HTTP 超时（默认 120s） |

## 使用

```python
from ff14_news import FF14News

news = FF14News(enable_cn_weibo=False)

# 并行抓取已启用渠道（列表级，blocks 为空）
bundle = news.fetch_articles(limit=2)
for channel_id, feed in bundle.feeds.items():
    print(channel_id, len(feed.articles))
for err in bundle.errors:
    print(err.channel_id, err.message)

# 单渠道
feed = news.cn_official.fetch_articles(limit=2)
feed = news.channel("cn_official").fetch_articles_by_ids(["387965"])

# 单篇正文
article = news.cn_official.fetch_article_detail("387965")
```

## 示例

`example.bat` 默认并行抓取**全部三个渠道、每渠道 5 条**，在终端以聊天消息样式展示（含头图，**textual-image**；Windows Terminal ≥ 1.22 或 VS Code 开 `terminal.integrated.enableImages` 时最清晰）。

```bat
example.bat
example.bat -n 10
```

首次运行会下载 Chromium（约 180MB）。若微博仍失败，可改用手动 Cookie：`example/weibo_cookie.txt`。

## 测试

```bat
pip install -e ".[dev]"
pytest

set FF14_NEWS_INTEGRATION=1
pytest tests/test_integration.py
```
