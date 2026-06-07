# hotmeme

从社会热点出发，经发现源拿热搜话题，再按热词在小红书、微博等平台搜梗图与趣图；不自写爬虫，对接 hotpush、TikHub。

- 热点发现与内容搜图分层：先拿在讨论什么，再按热词取图
- 统一图片项：保留来源链接、作者、话题、审核状态与风险标签
- hotpush、TikHub 预留接口；须在配置中显式启用
- 每个接入独立文件，配置里 `enabled` 控制开关

## 设计特性

### 可选源

在 `cn` 下配置 `hotpush`（发现）、`tikhub`（搜图）。未写入配置的源不会加载。

### 热点发现

从自部署 hotpush 拉多平台热榜，得到当前在讨论什么。

### 内容搜图

用热词请求小红书、微博等搜索 API，从笔记、帖子里抽出可展示图片；由 TikHub 接入后提供。

### 发现到成图管线

拉热榜 → 粗分类 → 按热词搜图文 → 过滤去重排序。单源失败不影响其它源。

### 统一图片项

各平台数据都映射为同一结构，含话题、风险标签、审核状态；默认保留原文链接。

### 内容安全

默认过滤 NSFW、广告引流与敏感词；政治、暴力、色情类内容默认不返回。

### 单次爬取与增量

`HotMeme` 可实例化。`crawl_once()` 拉取所有已启用源，返回 `HotMemeCrawlPacket`；实例记住已见 ID，再次调用时仅 `new_items` / `new_topics` 为相对上次新增。

## API

| 方法 | 说明 |
| --- | --- |
| `crawl_once()` | 单次爬取全部已启用源，返回增量数据包 |
| `reset_seen()` | 清空已见 ID，下次全部视为新增 |
| `discover_topics` / `fetch_cn_hot` | 热点发现与成图 |

## 配置

### `cn.hotpush`

| 含义 | 默认 | 说明 |
| --- | --- | --- |
| 是否启用 | false | 自部署 hotpush 热榜发现 |
| `base_url` | 空 | 服务根地址，如 `http://127.0.0.1:8000` |

### `cn.tikhub`

| 含义 | 默认 | 说明 |
| --- | --- | --- |
| 是否启用 | false | 按热词搜图；须配置 `api_key` |
| `base_url` | `https://api.tikhub.io` | API 根地址 |

### `cn_pipeline`

| 含义 | 默认 | 说明 |
| --- | --- | --- |
| `topic_limit` | 10 | 参与搜图的热点数 |
| `images_per_topic` | 3 | 每个热点最多取图数 |
| `classify_topics` | true | 是否对热点粗分类 |
| `content_platforms` | xiaohongshu、weibo | 内容搜索目标平台 |

### `fetch`

| 键 | 默认 | 说明 |
| --- | --- | --- |
| `total_limit` | 50 | 聚合后最大返回条数 |
| `per_source_timeout` | 5 | 单源超时秒数 |
| `retries` | 1 | 单源重试次数 |

示例见 `example/`。
