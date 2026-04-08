# Action 参数手册

## set_switch

控制单通道设备开关。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| device | str | 是 | 设备 ID |
| state | state | 是 | `"on"` / `"off"` |

## set_outlet

控制多通道设备的某一个通道。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| device | str | 是 | 设备 ID |
| outlet | int | 是 | 通道编号（从 0 开始） |
| state | state | 是 | `"on"` / `"off"` |

## set_outlets

同时控制多个通道。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| device | str | 是 | 设备 ID |
| switches | list | 是 | 通道列表，每项含 `outlet` (int) 和 `state` (state) |

## pulse_outlet

脉冲控制：开启指定通道 → 等待 → 自动关闭。

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| device | str | 是 | | 设备 ID |
| outlet | int | 是 | | 通道编号 |
| hold_seconds | float | 否 | 0.5 | 保持时长（秒），必须 > 0 |

## set_params

原始参数透传，直接发送任意 params 到设备。当以上 action 不能满足需求时使用。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| device | str | 是 | 设备 ID |
| params | dict | 是 | 发送给设备的原始参数 |