# ff14_the_hunt

从 [Bear Tracker](https://tracker.beartoolkit.com/timer) 拉取狩猎计时，解析触发窗/条件窗，并判断「刚刷新」。

## 用法

构造时直接传入数据中心、世界、Rank 等参数；之后可手动爬取或启动自动轮询。

```python
from ff14_the_hunt import FF14TheHunt, HuntRankKind

hunt = FF14TheHunt(
    data_centers=["猫小胖"],
    worlds=["静语庄园"],
    rank_kinds=[HuntRankKind.S, HuntRankKind.A],
    patches=["金曦之遗辉"],
)

packet = hunt.crawl_once()
recent = hunt.recently_spawned()
```

临时换筛选条件时仍可用 ``HuntQueryFilter`` 传给 ``query_marks`` / ``recently_spawned``。

默认 **不** 返回无触发/条件/FATE 计时的占位行（如 SS 级噬灵王、维护占位）；与 Bear Tracker 主列表一致。需要完整 API 原始行时设 ``include_untimed_marks=True``（构造参数或 ``HuntQueryFilter`` 字段均可）。

## 自动轮询与回调

轮询按上次结果分三种模式（见包内设计笔记 ``ff14_the_hunt-package-design``）：

- **全未开窗**：睡到筛选内最短「距离开窗」再爬（下限默认 2 分钟），此期间不叠固定间隔。
- **已有开窗/强制期/刚刷新/FATE 进行中**：短间隔轮询（默认 10 分钟；有刚刷新条目时默认 5 分钟）。
- **无触发计时**：退回固定间隔（默认 30 分钟）。

构造参数 ``active_poll_interval_seconds``、``recent_poll_interval_seconds``、``fallback_poll_interval_seconds``、``min_wakeup_seconds`` 可配。``poll_interval_seconds`` 已废弃，等同 ``fallback_poll_interval_seconds``。

```python
@hunt.on_crawl
def on_hunt(packet):
    print(len(packet.marks), "条", packet.crawled_at)

# 后台线程
hunt.start()
# ...
hunt.stop()

# 或阻塞到 Ctrl+C
hunt.run()
```

也可用实例作装饰器：`@hunt`。

单次爬取结果在 ``HuntCrawlPacket`` 里，含 ``crawled_at``、``next_fetch_at``、``marks``、``query``。

## 示例

```bat
example.bat
```

或 `python -m example`。输出写入 `example/output/`（已列入 `.gitignore`），JSON 使用 ``crawl_packet_to_display_dict`` 生成；语言默认跟随所选数据中心（中国区为中文狩猎名与地图区域，国际区为英文）。

## API 说明

| 站点接口 | 用途 |
| --- | --- |
| `POST /api/syncSession` | 狩猎库、刷点坐标、数据中心/世界列表 |
| `POST /api/lastDeathTimers` | 计时行；`RankType` 为 `aRank` / `sRank` / `fate` |
| `POST /api/querySpawnPoints` | 刚刷新记录的非触发点认证状态（需 `LastDeath`） |

刚刷新记录才填充 ``spawn_points``、``spawn_map_layout`` 与 ``region_map``。包内不标点、不裁剪；``region_map`` 为站点 ``HuntRegions`` 原图 base64。刷点仅保留未被 Sonar 或玩家认证为非触发的绿色候选点，含 ``地图X/Y``、``格点X/Y``、``像素X/Y``（按原图尺寸算好）；``地图布局`` 含格点尺度与归一化公式。默认 ``include_spawn_maps=True`` 拉取原图。示例 ``python -m example`` 将 PNG 写入 ``example/output/maps/``，JSON 用 ``区域地图.地图文件`` 引用。

`QueryDeathTimers` 为世界名列表（由所选数据中心展开）。

构造参数 ``patches`` 可写 Bear Tracker 缩写（如 ``DT``）或中文资料片名（如 ``金曦之遗辉``）；内部统一为 `Patch` 字段。``crawl_packet_to_display_dict`` 可按 ``locale`` 或 ``detect_display_locale`` 推断的语言导出；也可显式传入 ``HuntDisplayLocale.ZH`` / ``EN``。

触发时间窗算法与站点前端主计时列一致；带 `fateLastSeen` / `fateLastDeath` 的 7.0 S 链写入 ``fate_timer``。部分老式 S（如 Laideronnette）的天气条件窗尚未移植。

每条 ``TimerDisplay`` 含 ``bar_color``（站点 MUI 色键）与 ``hex_color``（Bear Tracker 主题主色），便于自建界面与网页同色展示：

| 表头 | 站点说明 | bar_color | hex |
| --- | --- | --- | --- |
| 触发时间 | 红：不可触发期（倒计时） | error | #e31a1a |
| 触发时间 | 绿：可触发期（正计时，% 为进度） | success | #01b574 |
| 触发时间 | 蓝：强制期（正计时） | info | #0075ff |
| 条件时间 | 红：未满足条件（倒计时） | error / warning | #e31a1a / #ffb547 |
| 条件时间 | 绿：已满足条件（倒计时） | success | #01b574 |
| FATE | 绿：距最近发现 | success | #01b574 |
| FATE | 红：距上次死亡 | error | #e31a1a |

``counts_up`` 标明正计时或倒计时。条件时间行待天气/月相逻辑移植后填充 ``condition_timer``。

「刚刷新」：触发窗开启后默认 15 分钟内，或 `lastMarkTime` 在默认 15 分钟内。
