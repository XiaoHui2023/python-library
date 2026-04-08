import asyncio
import hashlib
import json
import logging
import random
import socket
import time
from asyncio import DatagramProtocol, Future
from asyncio.protocols import BaseProtocol
from asyncio.transports import DatagramTransport
from typing import Union

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

_LOGGER = logging.getLogger(__name__)

HELLO = bytes.fromhex(
    "21310020ffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
)


class BasemiIO:
    device_id = None
    delta_ts = None

    def __init__(self, host: str, token: str, timeout: float = 3):
        self.addr = (host, 54321)
        self.token = bytes.fromhex(token)
        self.timeout = timeout

        key = hashlib.md5(self.token).digest()
        iv = hashlib.md5(key + self.token).digest()
        self.cipher = Cipher(
            algorithms.AES(key), modes.CBC(iv), backend=default_backend()
        )

    def _encrypt(self, plaintext: bytes):
        padder = padding.PKCS7(128).padder()
        padded_plaintext = padder.update(plaintext) + padder.finalize()
        encryptor = self.cipher.encryptor()
        return encryptor.update(padded_plaintext) + encryptor.finalize()

    def _decrypt(self, ciphertext: bytes):
        decryptor = self.cipher.decryptor()
        padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        return unpadder.update(padded_plaintext) + unpadder.finalize()

    def _pack_raw(self, msg_id: int, method: str, params: Union[dict, list] = None):
        payload = (
            json.dumps(
                {"id": msg_id, "method": method, "params": params or []},
                separators=(",", ":"),
            ).encode()
            + b"\x00"
        )
        data = self._encrypt(payload)

        raw = b"\x21\x31"
        raw += (32 + len(data)).to_bytes(2, "big")
        raw += b"\x00\x00\x00\x00"
        raw += self.device_id.to_bytes(4, "big")
        raw += int(time.time() - self.delta_ts).to_bytes(4, "big")
        raw += hashlib.md5(raw + self.token + data).digest()
        raw += data

        assert len(raw) < 1024, "Exceeded message size"
        return raw

    def _unpack_raw(self, raw: bytes):
        assert raw[:2] == b"\x21\x31"
        return self._decrypt(raw[32:])


class SyncMiIO(BasemiIO):
    def ping(self, sock: socket.socket) -> bool:
        try:
            sock.sendto(HELLO, self.addr)
            raw = sock.recv(1024)
            if raw[:2] == b"\x21\x31":
                self.device_id = int.from_bytes(raw[8:12], "big")
                self.delta_ts = time.time() - int.from_bytes(raw[12:16], "big")
                return True
        except Exception:
            pass
        return False

    def send(self, method: str, params: Union[dict, list] = None):
        pings = 0
        for times in range(1, 4):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(self.timeout)

                if self.delta_ts is None and not self.ping(sock):
                    pings += 1
                    continue

                msg_id = random.randint(100000000, 999999999)
                raw_send = self._pack_raw(msg_id, method, params)
                sock.sendto(raw_send, self.addr)
                raw_recv = sock.recv(10240)
                data = self._unpack_raw(raw_recv).rstrip(b"\x00")

                if data == b"":
                    data = {"result": ""}
                    break

                data = json.loads(data)
                if data["id"] == msg_id:
                    break

            except socket.timeout:
                pass
            except Exception:
                pass

            self.delta_ts = None
        else:
            return None

        if "result" in data:
            return data["result"]
        return None

    def send_bulk(self, method: str, params: list):
        try:
            result = []
            for i in range(0, len(params), 15):
                result += self.send(method, params[i : i + 15])
            return result
        except Exception:
            return None

    def info(self) -> Union[dict, str, None]:
        return self.send("miIO.info")


class _AsyncSocket(DatagramProtocol):
    timeout = 0
    transport: DatagramTransport = None
    response: Future = None

    def __init__(self):
        self.response = asyncio.get_event_loop().create_future()

    def connection_made(self, transport: DatagramTransport):
        self.transport = transport

    def datagram_received(self, data: bytes, addr):
        self.response.set_result(data)

    def settimeout(self, value: int):
        self.timeout = value

    def sendto(self, data: bytes):
        self.transport.sendto(data)

    def close(self):
        if not self.transport:
            return
        try:
            self.transport.close()
        except Exception:
            pass

    async def connect(self, addr: tuple[str, int]):
        coro = asyncio.get_event_loop().create_datagram_endpoint(
            lambda: self, remote_addr=addr
        )
        if self.timeout:
            await asyncio.wait_for(coro, self.timeout)
        else:
            await coro

    async def recv(self, *args):
        self.response = asyncio.get_event_loop().create_future()
        if self.timeout:
            return await asyncio.wait_for(self.response, self.timeout)
        return await self.response


class AsyncMiIO(BasemiIO, BaseProtocol):
    async def ping(self, sock: _AsyncSocket) -> bool:
        try:
            sock.sendto(HELLO)
            raw = await sock.recv(1024)
            if raw[:2] == b"\x21\x31":
                self.device_id = int.from_bytes(raw[8:12], "big")
                self.delta_ts = time.time() - int.from_bytes(raw[12:16], "big")
                return True
        except Exception:
            pass
        return False

    async def send(
        self, method: str, params: Union[dict, list] = None, tries: int = 3
    ) -> dict | None:
        offline = False
        for _ in range(0, tries):
            sock = _AsyncSocket()
            sock.settimeout(self.timeout)
            try:
                await sock.connect(self.addr)

                if self.delta_ts is None and not await self.ping(sock):
                    offline = True
                    continue

                msg_id = random.randint(100000000, 999999999)
                raw_send = self._pack_raw(msg_id, method, params)
                sock.sendto(raw_send)
                raw_recv = await sock.recv(10240)
                data = self._unpack_raw(raw_recv).rstrip(b"\x00")

                if data == b"":
                    continue

                data = json.loads(data)
                if data["id"] != msg_id:
                    continue

                return data

            except (asyncio.TimeoutError, OSError):
                pass
            except Exception as e:
                _LOGGER.debug("%s | %s", self.addr[0], method, exc_info=e)
            finally:
                sock.close()

            self.delta_ts = None

        if offline:
            _LOGGER.debug("%s | Device offline", self.addr[0])
            return None

        _LOGGER.debug("%s | No answer on %s %s", self.addr[0], method, params)
        return {}

    async def send_bulk(
        self, method: str, params: list, chunk: int = 0
    ) -> list | None:
        if not chunk:
            chunk = 15
        try:
            result = []
            for i in range(0, len(params), chunk):
                resp = await self.send(method, params[i : i + chunk])
                result += resp["result"]
            return result
        except Exception:
            return None

    async def info(self, tries: int = 3) -> dict | None:
        resp = await self.send("miIO.info", tries=tries)
        return resp.get("result") if resp else resp