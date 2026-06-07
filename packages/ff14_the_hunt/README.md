# ff14_the_hunt

从 [Bear Tracker](https://tracker.beartoolkit.com/timer) 拉取狩猎计时，解析触发窗/条件窗，并判断「刚刷新」。

## 用法

```python
from ff14_the_hunt import FF14TheHunt, HuntQueryFilter, HuntRankKind

hunt = FF14TheHunt()
marks = hunt.query_marks(
    HuntQueryFilter(
        data_centers=["猫小胖"],
        worlds=["静语庄园"],
        rank_kinds=[HuntRankKind.S, HuntRankKind.A],
        patches=["DT"],
    )
)
recent = hunt.recently_spawned(
    HuntQueryFilter(
        data_centers=["猫小胖"],
        worlds=["静语庄园"],
        rank_kinds=[HuntRankKind.S],
    )
)
```

## 示例

```bat
example.bat
```

或 `python -m example`。输出写入 `example/output/`（已列入 `.gitignore`）。

## API 说明

| 站点接口 | 用途 |
| --- | --- |
| `POST /api/syncSession` | 狩猎库、刷点坐标、数据中心/世界列表 |
| `POST /api/lastDeathTimers` | 计时行；`RankType` 为 `aRank` / `sRank` / `fate` |
| `POST /api/querySpawnPoints` | 各刷点是否已激活（需 `LastDeath`） |

`QueryDeathTimers` 为世界名列表（由所选数据中心展开）。

资料片筛选使用资源库中的 `Patch` 字段（7.0 金曦之遗辉 → `DT`）。

触发时间窗算法与站点前端主计时列一致；带 `fateLastSeen` / `fateLastDeath` 的 7.0 S 链使用 FATE 条件计时。部分老式 S（如 Laideronnette）的天气条件窗尚未移植。

「刚刷新」：触发窗开启后默认 15 分钟内，或 `lastMarkTime` 在默认 15 分钟内。
