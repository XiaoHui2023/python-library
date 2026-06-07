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

- `NewsFeed`：`channel_id`、列表 URL、`articles`（顺序与对应站点列表一致）。
- `NewsArticle`：列表级字段（`channel_id`、标题、摘要、头图、`source_page_url`）；默认 `blocks` 为空。
- 正文块：调用各渠道 `fetch_article_detail`（`fetch_article` 为别名）后 `blocks` 才有内容。

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

- 账号 `@cnff14`（uid `1784473157`）；列表自 m.weibo.cn 用户微博 tab。
- 反爬：依赖 [crawl4weibo](https://pypi.org/project/crawl4weibo/) + **Playwright Chromium**（`example.bat` 默认经代理 `127.0.0.1:7897` 安装内核并取 Cookie）。
- 默认无 Cookie 时由 Playwright 打开移动端页获取会话；API 经 `add_proxy` 走同一代理。也可手动配置 `cn_weibo_cookie` 或 `example/weibo_cookie.txt`。
- `fetch_articles`：时间线列表级字段，不拉长文展开。
- `fetch_articles_by_ids`：时间线查找或单条元数据，无 blocks。
- `fetch_article_detail`：完整正文（含长文展开）。
- 文章 `id` 为微博 mblog id 字符串。

## 配置

| 项 | 说明 |
| --- | --- |
| `FF14News().cn_official.category_code` | 列表栏目，默认 `5310` |
| `FF14News(cn_official_timeout_seconds=…)` | 国服渠道 HTTP 超时 |
| `FF14News(cn_weibo_timeout_seconds=…)` | 微博渠道 HTTP 超时（默认 60s） |
| `FF14News(cn_weibo_cookie=…)` | 微博 Cookie 整串（跳过 Playwright 取 Cookie） |
| `FF14News(cn_weibo_cookie_storage_path=…)` | Playwright 会话缓存路径 |
| `FF14News(cn_weibo_browser_headless=…)` | 自动取 Cookie 时是否无头浏览器（默认 True） |
| `FF14News(cn_weibo_proxy_url=…)` | 微博 HTTP 代理，如 `127.0.0.1:7897` |
| `FF14News(jp_official_timeout_seconds=…)` | 日文渠道 HTTP 超时（默认 120s） |

## 使用

```python
from ff14_news import FF14News

news = FF14News()

# 列表级（blocks 为空）
feed = news.cn_official.fetch_articles(limit=2)
feed_wb = news.cn_weibo.fetch_articles(limit=2)
feed_jp = news.jp_official.fetch_articles(limit=2)
feed = news.channel("cn_official").fetch_articles_by_ids(["387965"])

# 单篇正文
article = news.cn_official.fetch_article_detail("387965")

print(feed.model_dump_json(indent=2, ensure_ascii=False))
```

## 示例

`example.bat` 默认抓取**全部渠道、每渠道 2 条**，按渠道分子目录，仅下载头图：

```
example/output/
  cn_official/
  cn_weibo/
  jp_official/
    feed.json
    {id}/article.json
    {id}/article.md
    {id}/images/cover.*
```

```bat
example.bat
example.bat --proxy 127.0.0.1:7897
example.bat -c cn_official -n 5
example.bat --proxy ""
```

首次运行会经代理下载 Chromium（约 180MB）。代理默认 `127.0.0.1:7897`，与本地 Clash 等一致时可不改。若仍失败，可改用手动 Cookie：`example/weibo_cookie.txt`。

## 测试

```bat
pip install -e ".[dev]"
pytest

set FF14_NEWS_INTEGRATION=1
pytest tests/test_integration.py
```
