# onebot-protocol

OneBot 通信协议，定义消息收发的公共数据结构。基于 OneBot 11 标准，使用 Pydantic 提供类型安全的模型定义。

## `MessagePayload`（OneBot 11 字段名）

| 字段 | 说明 |
|------|------|
| `post_type` | 事件类型，如 `message`（可选） |
| `message_type` | `group` 或 `private` |
| `self_id` | 机器人 QQ 号（可选） |
| `message_id` | 消息 ID；空时自动生成 UUID |
| `user_id` | 发送方 QQ；私聊时亦为会话对端 |
| `group_id` | 群号；群聊会话标识 |
| `message` | 消息段列表 |

解析时仍接受旧名别名：`source_type`→`message_type`、`bot_id`→`self_id`、`messages`→`message`、`session_id`→`group_id`/`user_id`。

## 特性

- 完整的消息段（Message Segment）类型：文本、提及、图片、语音、视频、文件、位置、回复等
- 图片、语音、音频、视频、文件段共用 `FileData`（`name`、`content`、`mime_type`、`size`）
- 支持 discriminated union，根据 `type` 字段自动解析消息类型

## 文件载荷 `FileData`

| 字段 | 说明 |
|------|------|
| `name` | 显示用文件名（可选） |
| `content` | 内容引用，如 URL、平台资源标识或 Base64 等（可选，编码由实现方约定） |
| `mime_type` | MIME 类型（可选） |
| `size` | 字节大小（可选） |

`image` / `voice` / `audio` / `video` / `file` 各段类型的 `data` 均为对应子类，字段与 `FileData` 相同。

## 支持的消息类型

| 类型 | 说明 |
|------|------|
| `text` | 纯文本 |
| `mention` | @某人 |
| `mention_all` | @所有人 |
| `image` | 图片 |
| `voice` | 语音 |
| `audio` | 音频 |
| `video` | 视频 |
| `file` | 文件 |
| `location` | 位置 |
| `reply` | 回复 |