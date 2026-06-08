# hotmeme

经 **TikHub** 从国内平台拉热门帖（图文或短视频），质检后渲染为可交付输出包。

- 数据源：TikHub（API key 由调用方传入）
- 默认平台：小红书、抖音
- 交付物：图或视频地址 + 标题/作者文案 + 原帖链接

## 设计特性

### 平台工作流

各平台对应独立拉帖策略，由 TikHub 不同接口组合完成：

| 平台 | 策略 |
| --- | --- |
| 抖音 | 热榜关键词 → 视频搜索（近一天、按点赞） |
| 小红书 | 热榜话题 → 笔记搜索（按热度） |

未接入工作流的平台标识会被跳过，不中断整轮拉取。

### 质检管线

拉取结果归一为热帖项后，依次丢弃无媒体条目、按 NSFW/风控/去重/排序过滤；API 返回多少条就保留多少条（仅质检剔除，不按条数截断）。

### 增量爬取

`crawl_once` 在实例内记忆已见 ID，每轮只交付相对上次的新增帖。

### 渲染输出

渲染器把通过质检的热帖项转为输出包：主媒体地址（图或视频）、缩略图、标题、含作者的展示文案、原帖链接。

## 配置

示例见 `example/config.example.yaml`。私密信息（TikHub API key）不入库，由调用参数或 `example/.env` 提供。

### `tikhub`

| 键 | 默认 | 说明 |
| --- | --- | --- |
| `enabled` | true | 是否启用 TikHub |
| `api_key` | — | TikHub API key（调用方传入） |
| `base_url` | `https://api.tikhub.io` | API 根地址 |
| `timeout` | 5 | 请求超时秒数 |
| `allow_nsfw` | false | 是否允许 NSFW |

### `pipeline`

| 键 | 默认 | 说明 |
| --- | --- | --- |
| `platforms` | 小红书、抖音 | 拉帖平台列表 |

### `fetch`

| 键 | 默认 | 说明 |
| --- | --- | --- |
| `per_source_timeout` | 5 | 单平台超时秒数 |
| `retries` | 1 | 失败重试次数 |
| `skip_failed_providers` | true | 单平台失败时是否跳过并继续 |

## 入口

| 入口 | 说明 |
| --- | --- |
| `HotMeme(api_key=...)` | 构造聚合器 |
| `HotMeme.fetch_hot_posts()` | 拉热帖并质检 |
| `HotMeme.crawl_once()` | 增量爬取 |
| `HotMeme.crawl_and_render()` | 爬取并渲染输出包 |
| `render_items(items)` | 把热帖项列表渲染为输出批次 |
| `supported_platforms()` | 已接入工作流的平台 |

本地试跑：复制 `example/.env.example` 为 `example/.env`，填入 `TIKHUB_API_KEY`，在包根目录执行 `example.bat`。
