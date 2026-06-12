import asyncio
import json
import sys
import time
from collections import OrderedDict
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Awaitable, Optional

VoidCallback = Callable[[], Awaitable[None]]
DisconnectCallback = Callable[[str], Awaitable[None]]
ErrorCallback = Callable[[BaseException], Awaitable[None]]
import aiohttp
from .models import QQMediaAttachment, QQSource, EVENT_SOURCE_MAP, QQMessage

DEFAULT_INTENTS = (1 << 0) | (1 << 1) | (1 << 25) | (1 << 30)

MSG_DEDUP_CACHE_SIZE = 1000
API_REQUEST_ATTEMPTS = 3
API_REQUEST_TIMEOUT_SECONDS = 15
API_RETRY_DELAYS = (1.0, 3.0)

API_BASE = "https://api.sgroup.qq.com"
AUTH_URL = "https://bots.qq.com/app/getAppAccessToken"
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
RETRYABLE_EXCEPTIONS = (
    aiohttp.ClientError,
    asyncio.TimeoutError,
    TimeoutError,
    OSError,
)


class QQBot:
    """QQ 开放平台网关客户端：鉴权、WebSocket 与按场景回复。

    构造入参见 __init__ 的 Args；包外请优先使用 Adapter。
    """

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        bot_id: str,
        proxy: Optional[str] = None,
        intents: int = DEFAULT_INTENTS,
    ) -> None:
        """绑定应用凭证并准备事件订阅掩码。

        Args:
            app_id: 开放平台应用 ID
            app_secret: 开放平台应用密钥
            bot_id: 机器人 ID，写入入站消息
            proxy: 可选 HTTP 代理
            intents: 网关 intents 位掩码

        Raises:
            ValueError: 未提供 bot_id
        """
        if bot_id is None:
            raise ValueError("bot_id is required")

        self.app_id = app_id
        self.app_secret = app_secret
        self.bot_id = bot_id
        self.proxy = proxy

        self._on_message: Callable[[QQMessage], Awaitable[None]] | None = None
        self._on_connect: VoidCallback | None = None
        self._on_ready: VoidCallback | None = None
        self._on_disconnect: DisconnectCallback | None = None
        self._on_error: ErrorCallback | None = None
        self._source: dict[str, QQSource] = {}
        self._intents = intents
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._hb_task: Optional[asyncio.Task] = None
        self._running = False
        self._seq: Optional[int] = None
        self._session_id: Optional[str] = None
        self._msg_seq: dict[str, int] = {}
        self._replied_msgs: OrderedDict[str, None] = OrderedDict()
        self._stop_event = asyncio.Event()
        self._ws_task: asyncio.Task[None] | None = None

    def on_message(self, callback: Callable[[QQMessage], Awaitable[None]]) -> None:
        """登记入站聊天事件回调。

        Args:
            callback: 异步处理包内 QQ 消息
        """
        self._on_message = callback

    def on_connect(self, callback: VoidCallback) -> None:
        """登记 WebSocket 已连接回调。"""
        self._on_connect = callback

    def on_ready(self, callback: VoidCallback) -> None:
        """登记网关 READY 回调。"""
        self._on_ready = callback

    def on_disconnect(self, callback: DisconnectCallback) -> None:
        """登记连接断开回调。

        Args:
            callback: 异步处理断开原因短句
        """
        self._on_disconnect = callback

    def on_error(self, callback: ErrorCallback) -> None:
        """登记运行期错误回调。

        Args:
            callback: 异步处理异常对象
        """
        self._on_error = callback

    async def _emit_connect(self) -> None:
        if self._on_connect is None:
            return
        try:
            await self._on_connect()
        except Exception:
            pass

    async def _emit_ready(self) -> None:
        if self._on_ready is None:
            return
        try:
            await self._on_ready()
        except Exception:
            pass

    async def _emit_disconnect(self, reason: str) -> None:
        if self._on_disconnect is None:
            return
        try:
            await self._on_disconnect(reason)
        except Exception:
            pass

    async def _emit_error(self, exc: BaseException) -> None:
        if self._on_error is None:
            return
        try:
            await self._on_error(exc)
        except Exception:
            pass

    async def _get_access_token(self) -> str:
        now = datetime.now(timezone.utc)
        if (
            self._access_token
            and self._token_expires_at
            and now < self._token_expires_at
        ):
            return self._access_token

        data = await self._request_json(
            "POST",
            AUTH_URL,
            json={
                "appId": self.app_id,
                "clientSecret": self.app_secret,
            },
        )

        if "access_token" not in data:
            raise RuntimeError(f"鉴权失败: {data}")

        self._access_token = data["access_token"]
        self._token_expires_at = now + timedelta(
            seconds=int(data["expires_in"]) - 30
        )
        return self._access_token

    async def _auth_headers(self) -> dict[str, str]:
        token = await self._get_access_token()
        return {
            "Authorization": f"QQBot {token}",
            "X-Union-Appid": self.app_id,
        }

    @property
    def _http(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            raise RuntimeError("QQBot 尚未启动, 请先调用 run()")
        return self._session

    async def _api_get(self, path: str) -> dict:
        headers = await self._auth_headers()
        return await self._request_json("GET", f"{API_BASE}{path}", headers=headers)

    async def _api_post(self, path: str, body: dict) -> dict:
        headers = await self._auth_headers()
        return await self._request_json(
            "POST",
            f"{API_BASE}{path}",
            headers=headers,
            json=body,
        )

    async def _request_json(self, method: str, url: str, **kwargs: Any) -> dict:
        timeout = aiohttp.ClientTimeout(total=API_REQUEST_TIMEOUT_SECONDS)
        last_error: BaseException | None = None
        for attempt in range(API_REQUEST_ATTEMPTS):
            try:
                async with self._http.request(
                    method,
                    url,
                    proxy=self.proxy,
                    timeout=timeout,
                    **kwargs,
                ) as resp:
                    text = await resp.text()
                    if resp.status in RETRYABLE_STATUS:
                        error = RuntimeError(
                            f"QQ API {method} {url} failed: {resp.status} {text[:200]}"
                        )
                        if attempt < API_REQUEST_ATTEMPTS - 1:
                            last_error = error
                            await asyncio.sleep(API_RETRY_DELAYS[attempt])
                            continue
                        raise error
                    if resp.status >= 400:
                        raise RuntimeError(
                            f"QQ API {method} {url} failed: {resp.status} {text[:200]}"
                        )
                    return json.loads(text) if text else {}
            except RETRYABLE_EXCEPTIONS as exc:
                if attempt >= API_REQUEST_ATTEMPTS - 1:
                    raise RuntimeError(
                        f"QQ API {method} {url} failed after "
                        f"{API_REQUEST_ATTEMPTS} attempts: {exc}"
                    ) from exc
                last_error = exc
                await asyncio.sleep(API_RETRY_DELAYS[attempt])

        raise RuntimeError(f"QQ API {method} {url} failed: {last_error}")

    async def reply_guild(self, channel_id: str, msg_id: str, content: str):
        await self._api_post(f"/channels/{channel_id}/messages", {
            "content": content,
            "msg_id": msg_id,
        })

    async def reply_group(self, group_openid: str, msg_id: str,
                          content: str, msg_seq: int = 1):
        await self._api_post(f"/v2/groups/{group_openid}/messages", {
            "msg_type": 0,
            "content": content,
            "msg_id": msg_id,
            "msg_seq": msg_seq,
            "timestamp": int(time.time()),
        })

    async def reply_c2c(self, openid: str, msg_id: str,
                        content: str, msg_seq: int = 1):
        await self._api_post(f"/v2/users/{openid}/messages", {
            "msg_type": 0,
            "content": content,
            "msg_id": msg_id,
            "msg_seq": msg_seq,
            "timestamp": int(time.time()),
        })

    async def upload_group_media(
        self,
        group_openid: str,
        media: QQMediaAttachment,
    ) -> str:
        result = await self._api_post(
            f"/v2/groups/{group_openid}/files",
            self._media_upload_body(media),
        )
        return str(result.get("file_info", ""))

    async def upload_c2c_media(
        self,
        openid: str,
        media: QQMediaAttachment,
    ) -> str:
        result = await self._api_post(
            f"/v2/users/{openid}/files",
            self._media_upload_body(media),
        )
        return str(result.get("file_info", ""))

    async def reply_group_media(
        self,
        group_openid: str,
        msg_id: str,
        content: str,
        file_info: str,
        msg_seq: int = 1,
    ) -> None:
        await self._api_post(f"/v2/groups/{group_openid}/messages", {
            "msg_type": 7,
            "content": content or " ",
            "msg_id": msg_id,
            "msg_seq": msg_seq,
            "media": {"file_info": file_info},
            "timestamp": int(time.time()),
        })

    async def reply_c2c_media(
        self,
        openid: str,
        msg_id: str,
        content: str,
        file_info: str,
        msg_seq: int = 1,
    ) -> None:
        body = {
            "msg_type": 7,
            "msg_id": msg_id,
            "msg_seq": msg_seq,
            "media": {"file_info": file_info},
            "timestamp": int(time.time()),
        }
        if content:
            body["content"] = content
        await self._api_post(f"/v2/users/{openid}/messages", body)

    @staticmethod
    def _media_upload_body(media: QQMediaAttachment) -> dict[str, object]:
        body: dict[str, object] = {
            "file_type": media.file_type,
            "srv_send_msg": False,
        }
        if media.url:
            body["url"] = media.url
        if media.file_data:
            body["file_data"] = media.file_data
        return body

    def next_seq(self, key: str) -> int:
        """为群聊或单聊回复递增序号，满足平台去重要求。

        Args:
            key: 会话或来源 ID

        Returns:
            本次应使用的 msg_seq
        """
        self._msg_seq[key] = self._msg_seq.get(key, 0) + 1
        return self._msg_seq[key]

    async def send_message(self, msg: QQMessage) -> None:
        """按消息内来源类型选择频道、群或单聊回复接口。

        Args:
            msg: 含正文与引用消息 ID 的包内消息
        """
        if msg.source_type:
            source_type = msg.source_type
        else:
            if msg.source_id in self._source:
                source_type = self._source[msg.source_id]
            else:
                raise RuntimeError(f"未知的 QQ 消息来源: {msg.source_id}")

        if source_type == QQSource.GUILD:
            await self.reply_guild(msg.source_id, msg.msg_id, msg.content)
        elif source_type == QQSource.GROUP:
            await self._send_group(msg)
        elif source_type == QQSource.C2C:
            await self._send_c2c(msg)
        else:
            return

    async def _send_group(self, msg: QQMessage) -> None:
        if not msg.media:
            seq = self.next_seq(msg.source_id)
            await self.reply_group(msg.source_id, msg.msg_id, msg.content, seq)
            return
        await self._send_group_media(msg)

    async def _send_c2c(self, msg: QQMessage) -> None:
        if not msg.media:
            seq = self.next_seq(msg.source_id)
            await self.reply_c2c(msg.source_id, msg.msg_id, msg.content, seq)
            return
        await self._send_c2c_media(msg)

    async def _send_group_media(self, msg: QQMessage) -> None:
        pending_text = msg.content
        sent_any = False
        for media in msg.media:
            file_info = await self.upload_group_media(msg.source_id, media)
            if not file_info:
                continue
            seq = self.next_seq(msg.source_id)
            await self.reply_group_media(
                msg.source_id,
                msg.msg_id,
                pending_text,
                file_info,
                seq,
            )
            pending_text = ""
            sent_any = True
        if not sent_any and msg.content:
            seq = self.next_seq(msg.source_id)
            await self.reply_group(msg.source_id, msg.msg_id, msg.content, seq)

    async def _send_c2c_media(self, msg: QQMessage) -> None:
        pending_text = msg.content
        sent_any = False
        for media in msg.media:
            file_info = await self.upload_c2c_media(msg.source_id, media)
            if not file_info:
                continue
            seq = self.next_seq(msg.source_id)
            await self.reply_c2c_media(
                msg.source_id,
                msg.msg_id,
                pending_text,
                file_info,
                seq,
            )
            pending_text = ""
            sent_any = True
        if not sent_any and msg.content:
            seq = self.next_seq(msg.source_id)
            await self.reply_c2c(msg.source_id, msg.msg_id, msg.content, seq)

    def _build_request(self, event_type: str, data: dict) -> Optional[QQMessage]:
        message_source = EVENT_SOURCE_MAP.get(event_type)
        if message_source is None:
            return None

        msg_id = data.get("id", "")
        content = data.get("content", "").strip()

        if message_source == QQSource.GUILD:
            session_id = data.get("channel_id", "")
            user_id = data.get("author", {}).get("id", "")
        elif message_source == QQSource.GROUP:
            session_id = data.get("group_openid", "")
            user_id = data.get("author", {}).get("member_openid", "")
        else:
            session_id = data.get("author", {}).get("user_openid", "")
            user_id = session_id

        msg = QQMessage(
            source_type=message_source,
            source_id=session_id,
            session_id=session_id,
            msg_id=msg_id,
            content=content,
            bot_id=self.bot_id,
            user_id=user_id,
        )

        self._source[msg.source_id] = message_source

        return msg

    def _mark_replied(self, msg_id: str) -> bool:
        if msg_id in self._replied_msgs:
            return False
        self._replied_msgs[msg_id] = None
        while len(self._replied_msgs) > MSG_DEDUP_CACHE_SIZE:
            self._replied_msgs.popitem(last=False)
        return True

    async def _dispatch_message(self, event_type: str, data: dict):
        msg = self._build_request(event_type, data)
        if msg is None:
            return

        if self._on_message is not None:
            asyncio.create_task(self._on_message(msg))

    async def _heartbeat_loop(self, ws: aiohttp.ClientWebSocketResponse,
                              interval: float):
        while True:
            await asyncio.sleep(interval)
            await ws.send_json({"op": 1, "d": self._seq})

    async def _handle_ws(self):
        try:
            while self._running:
                reason = await self._try_connect()
                if not self._running or reason == "stopped":
                    break
                if reason == "invalid_session":
                    self._session_id = None
                    self._seq = None
                await asyncio.sleep(5)
        finally:
            await self._cleanup()

    async def start(self) -> None:
        """启动 HTTP 会话并在后台维持网关连接。"""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._session = aiohttp.ClientSession()
        self._ws_task = asyncio.create_task(self._handle_ws())

    async def _try_connect(self) -> str:
        if self._session_id and self._seq is not None:
            try:
                reason = await self._resume()
                if reason != "invalid_session":
                    return reason
            except Exception:
                pass
            self._session_id = None
            self._seq = None
        try:
            return await self._connect()
        except Exception as exc:
            await self._emit_error(exc)
            return "error"

    async def _connect(self) -> str:
        token = await self._get_access_token()

        gw = await self._api_get("/gateway/bot")
        if "url" not in gw:
            raise RuntimeError(f"获取网关失败, 请检查 APP_ID/APP_SECRET: {gw}")
        ws_url = gw["url"]

        self._ws = await self._http.ws_connect(ws_url, proxy=self.proxy)
        await self._emit_connect()
        try:
            hello = await self._ws.receive_json()
            if hello.get("op") != 10:
                raise RuntimeError(f"期望 Hello(op=10), 收到 {hello}")
            heartbeat_interval = hello["d"]["heartbeat_interval"] / 1000

            await self._ws.send_json({
                "op": 2,
                "d": {
                    "token": f"QQBot {token}",
                    "intents": self._intents,
                    "shard": [0, 1],
                    "properties": {
                        "$os": sys.platform,
                        "$language": f"python {sys.version}",
                        "$sdk": "qq-adapter",
                    },
                },
            })

            ready = await self._ws.receive_json()
            if ready.get("op") == 9:
                raise RuntimeError(f"鉴权失败 (Invalid Session): {ready}")
            if ready.get("op") != 0 or ready.get("t") != "READY":
                raise RuntimeError(f"期望 Ready 事件, 收到 {ready}")

            self._session_id = ready["d"]["session_id"]
            self._seq = ready.get("s")
            await self._emit_ready()

            self._hb_task = asyncio.create_task(
                self._heartbeat_loop(self._ws, heartbeat_interval)
            )

            reason = await self._event_loop(self._ws)
            await self._emit_disconnect(reason)
            return reason
        finally:
            if self._hb_task:
                self._hb_task.cancel()
                self._hb_task = None
            if not self._ws.closed:
                await self._ws.close()

    async def _resume(self) -> str:
        token = await self._get_access_token()

        gw = await self._api_get("/gateway/bot")
        if "url" not in gw:
            raise RuntimeError(f"获取网关失败: {gw}")
        ws_url = gw["url"]

        self._ws = await self._http.ws_connect(ws_url, proxy=self.proxy)
        await self._emit_connect()
        try:
            hello = await self._ws.receive_json()
            if hello.get("op") != 10:
                raise RuntimeError(f"期望 Hello(op=10), 收到 {hello}")
            heartbeat_interval = hello["d"]["heartbeat_interval"] / 1000

            await self._ws.send_json({
                "op": 6,
                "d": {
                    "token": f"QQBot {token}",
                    "session_id": self._session_id,
                    "seq": self._seq,
                },
            })

            self._hb_task = asyncio.create_task(
                self._heartbeat_loop(self._ws, heartbeat_interval)
            )
            reason = await self._event_loop(self._ws)
            await self._emit_disconnect(reason)
            return reason
        finally:
            if self._hb_task:
                self._hb_task.cancel()
                self._hb_task = None
            if not self._ws.closed:
                await self._ws.close()

    async def _event_loop(self, ws: aiohttp.ClientWebSocketResponse) -> str:
        async for msg in ws:
            if not self._running:
                return "stopped"

            if msg.type == aiohttp.WSMsgType.TEXT:
                payload = json.loads(msg.data)
                op = payload.get("op")

                if payload.get("s") is not None:
                    self._seq = payload["s"]

                if op == 0:
                    event_type = payload.get("t", "")
                    await self._dispatch_message(event_type, payload.get("d", {}))
                elif op == 7:
                    return "reconnect"
                elif op == 9:
                    return "invalid_session"

            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                return "closed"
        return "closed"

    async def stop(self) -> None:
        """关闭 WebSocket 并通知等待中的常驻运行结束。"""
        if not self._running:
            self._stop_event.set()
            return
        self._running = False
        if self._hb_task:
            self._hb_task.cancel()
            self._hb_task = None
        if self._ws and not self._ws.closed:
            await self._ws.close()
        self._stop_event.set()
        if self._ws_task is not None and self._ws_task is not asyncio.current_task():
            self._ws_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._ws_task
        self._ws_task = None

    async def _cleanup(self):
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def run(self) -> None:
        """启动连接并阻塞；Ctrl+C 或任务取消时收尾退出。"""
        await self.start()
        try:
            await self._stop_event.wait()
        finally:
            await self.stop()
