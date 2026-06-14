"""Async Longshi Cloud protocol client."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import secrets
import string
import time
from dataclasses import dataclass
from typing import Any

import websockets
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

ROOT_URLS = {
    "cn": ("ws://rsroot.rongsee.net:65002", 86),
    "asia": ("ws://rsroot-xjp.audiocam.net:65002", 65),
    "us": ("ws://rsroot-us.audiocam.net:65002", 1),
}
MASTER_KEY = "MasteryAppkey001"
MASTER_IV = "Mastery-IVkey001"


class LongshiError(Exception):
    """Base Longshi Cloud error."""


class LongshiAuthError(LongshiError):
    """Longshi Cloud authentication error."""


class LongshiConnectionError(LongshiError):
    """Longshi Cloud connection error."""


def md5(value: str) -> str:
    """Return an MD5 digest used by the vendor protocol."""
    return hashlib.md5(value.encode()).hexdigest()


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def random_string(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def aes_encrypt(iv: str, key: str, plaintext: str) -> str:
    cipher = AES.new(key.encode(), AES.MODE_CBC, iv.encode())
    return base64.b64encode(
        cipher.encrypt(pad(plaintext.encode(), AES.block_size))
    ).decode()


def aes_decrypt(iv: str, key: str, ciphertext: str) -> str:
    cipher = AES.new(key.encode(), AES.MODE_CBC, iv.encode())
    return unpad(cipher.decrypt(base64.b64decode(ciphertext)), AES.block_size).decode()


def b64_encode(value: str) -> str:
    return base64.b64encode(value.encode()).decode()


def b64_decode(value: str) -> str:
    return base64.b64decode(value).decode()


@dataclass
class LongshiDevice:
    """A device returned by Longshi Cloud."""

    cid: str
    shared: bool
    owner: str
    info: dict[str, Any]
    config: dict[str, Any]

    @property
    def name(self) -> str:
        return str(self.info.get("name") or self.cid)


class LongshiCloudClient:
    """Authenticate with Longshi Cloud and discover devices."""

    def __init__(
        self, account: str, password: str, timeout: float = 12, region: str = "auto"
    ):
        self.account = account
        self.password = password
        self.timeout = timeout
        self.password_hash = md5(password + account + MASTER_KEY)
        self.account_hash = md5(account + MASTER_KEY)
        self.server_key = ""
        self.user_id = ""
        self.token = random_string()
        self.regions = list(ROOT_URLS) if region == "auto" else [region]
        self.region: str | None = None

    @property
    def zone(self) -> int:
        return ROOT_URLS[self.region or "cn"][1]

    def _aes_key(self) -> str:
        return md5(self.password_hash + self.account + self.server_key + MASTER_KEY)

    async def _recv(self, websocket: Any) -> dict[str, Any]:
        try:
            message = await asyncio.wait_for(websocket.recv(), self.timeout)
            raw = json.loads(message)
            if raw.get("v") and raw.get("d"):
                return json.loads(aes_decrypt(raw["v"], self._aes_key(), raw["d"]))
            return raw
        except asyncio.TimeoutError as exc:
            raise LongshiConnectionError("Cloud response timed out") from exc

    async def _send(
        self, websocket: Any, request: dict[str, Any], login: bool = False
    ) -> None:
        iv = random_string()
        envelope = {
            "v": iv,
            "d": aes_encrypt(iv, self._aes_key(), compact_json(request)),
        }
        if login:
            envelope["a"] = self.account_hash
        await websocket.send(compact_json(envelope))

    async def async_list_devices(self) -> list[LongshiDevice]:
        errors: list[str] = []
        auth_errors = 0
        for region in self.regions:
            try:
                return await self._list_devices_from_region(region)
            except LongshiAuthError as exc:
                auth_errors += 1
                errors.append(f"{region}: {exc}")
            except Exception as exc:
                errors.append(f"{region}: {exc}")
        if auth_errors == len(self.regions):
            raise LongshiAuthError("; ".join(errors))
        raise LongshiConnectionError("; ".join(errors))

    async def _list_devices_from_region(self, region: str) -> list[LongshiDevice]:
        self.server_key = ""
        try:
            async with websockets.connect(
                ROOT_URLS[region][0], open_timeout=self.timeout
            ) as websocket:
                timestamp = int(time.time() * 1000)
                await self._send(
                    websocket,
                    {
                        "req": "login",
                        "account": self.account,
                        "date": timestamp,
                        "appsts": 1,
                        "pwd": md5(self.password_hash + self.account + str(timestamp)),
                    },
                    login=True,
                )
                response = await self._recv(websocket)
                if response.get("res") != "login" or response.get("errno") != 0:
                    raise LongshiAuthError(
                        f"Login failed with errno {response.get('errno')}"
                    )

                self.region = region
                self.server_key = response["key"]
                self.user_id = str(response.get("usrid", ""))
                await self._send(websocket, {"req": "getDevices"})
                response = await self._recv(websocket)
                if response.get("res") != "getDevices" or response.get("errno", 0) != 0:
                    raise LongshiConnectionError(
                        f"getDevices failed: {response.get('errno')}"
                    )
                return self._decode_devices(response.get("dev", {}))
        except (LongshiAuthError, LongshiConnectionError):
            raise
        except Exception as exc:
            raise LongshiConnectionError(str(exc)) from exc

    def _decode_devices(self, raw_devices: dict[str, Any]) -> list[LongshiDevice]:
        devices = []
        for cid, raw in raw_devices.items():
            info = json.loads(b64_decode(raw["devinfo"]))
            shared = str(raw.get("from", "")) != self.user_id
            if shared:
                config = json.loads(b64_decode(raw["devcfg"]))
            else:
                key = md5(self.account + self.password + info["slat"])
                config = json.loads(aes_decrypt(MASTER_IV, key, raw["devcfg"]))
            devices.append(
                LongshiDevice(cid, shared, str(raw.get("from", "")), info, config)
            )
        return devices


class LongshiDeviceClient:
    """Open a short-lived session to one Longshi recording device."""

    def __init__(
        self, cloud: LongshiCloudClient, device: LongshiDevice, zone: int | None = None
    ):
        self.cloud = cloud
        self.device = device
        self.zone = zone or cloud.zone
        self.timeout = cloud.timeout
        self.client_id = 1
        self.gateway_alive_date: int | None = None
        self.gateway_online = False
        self.device_iv: str | None = None
        self.device_key = md5(device.config["pwd"] + device.cid)[:16]

    async def _recv(self, websocket: Any) -> dict[str, Any]:
        try:
            return json.loads(await asyncio.wait_for(websocket.recv(), self.timeout))
        except asyncio.TimeoutError as exc:
            raise LongshiConnectionError(f"Device {self.device.cid} timed out") from exc

    async def _send(self, websocket: Any, value: dict[str, Any]) -> None:
        await websocket.send(compact_json(value))

    def _decode_device_message(self, value: dict[str, Any]) -> dict[str, Any] | None:
        if value.get("req") != "tocli" or not value.get("data"):
            return None
        plaintext = (
            aes_decrypt(self.device_iv or "", self.device_key, value["data"])
            if "v" in value
            else b64_decode(value["data"])
        )
        return json.loads(plaintext)

    async def _send_to_device(self, websocket: Any, request: dict[str, Any]) -> None:
        if self.device_iv is None:
            data = b64_encode(compact_json(request))
            await self._send(
                websocket, {"req": "tohost", "id": self.client_id, "data": data}
            )
            return
        data = aes_encrypt(self.device_iv, self.device_key, compact_json(request))
        await self._send(
            websocket, {"req": "tohost", "id": self.client_id, "v": "", "data": data}
        )

    async def _wait_for_device(self, websocket: Any, expected: str) -> dict[str, Any]:
        while True:
            message = self._decode_device_message(await self._recv(websocket))
            if message and message.get("res") == expected:
                return message

    async def async_run(self, requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
        url = f"ws://{self.device.config['url']}:{self.device.config['port']}"
        try:
            async with websockets.connect(
                url, open_timeout=self.timeout, close_timeout=1
            ) as websocket:
                await self._login(websocket)
                responses = []
                for request in requests:
                    await self._send_to_device(websocket, request)
                    responses.append(
                        await self._wait_for_device(websocket, request["req"])
                    )
                return responses
        except LongshiConnectionError:
            raise
        except Exception as exc:
            raise LongshiConnectionError(str(exc)) from exc

    async def async_set_and_verify(
        self, request: dict[str, Any], verify_request: str, field: str
    ) -> dict[str, Any]:
        """Send a setting and wait until the device reports the requested value."""
        url = f"ws://{self.device.config['url']}:{self.device.config['port']}"
        try:
            async with websockets.connect(
                url, open_timeout=self.timeout, close_timeout=1
            ) as websocket:
                await self._login(websocket)
                expected = request[field]
                for _ in range(3):
                    await self._send_to_device(websocket, request)
                    await asyncio.sleep(0.2)
                    await self._send_to_device(websocket, {"req": verify_request})
                    response = await self._wait_for_device(websocket, verify_request)
                    value = response.get("value", {})
                    actual = value.get(field) if isinstance(value, dict) else value
                    if actual == expected:
                        return response
                raise LongshiConnectionError(
                    f"Device did not apply {field}={expected}; last value was {actual}"
                )
        except LongshiConnectionError:
            raise
        except Exception as exc:
            raise LongshiConnectionError(str(exc)) from exc

    async def _login(self, websocket: Any) -> None:
        await self._send(
            websocket, {"req": "login", "nid": int(self.device.cid[10:], 36)}
        )
        response = await self._recv(websocket)
        if response.get("res") != "login" or response.get("errno", 0) != 0:
            raise LongshiConnectionError(
                f"Gateway login failed: {response.get('errno')}"
            )

        digest = bytes.fromhex(md5(self.device.config["pwd"] + self.device.cid))
        pwd22 = base64.b64encode(digest).decode()[:22]
        gateway_pwd = base64.b64encode(
            bytes.fromhex(md5(pwd22 + response["key"]))
        ).decode()
        await self._send(
            websocket,
            {
                "req": "idf",
                "token": self.cloud.token,
                "account": md5(self.cloud.account),
                "pwd": gateway_pwd,
                "zone": self.zone,
            },
        )
        response = await self._recv(websocket)
        if response.get("res") != "idf" or response.get("errno", 0) != 0:
            raise LongshiConnectionError(
                f"Gateway identification failed: {response.get('errno')}"
            )
        self.client_id = int(response.get("id", 1))
        self.gateway_alive_date = response.get("aliveDate")
        self.gateway_online = bool(response.get("online"))

        await self._send(websocket, {"req": "wakeup"})
        response = await self._wait_for_device_login(websocket)
        self.device_iv = response["v"]
        await self._send_to_device(
            websocket,
            {
                "req": "idf",
                "account": self.cloud.account,
                "uuid": self.device.config["uuid"],
            },
        )
        response = await self._wait_for_device(websocket, "idf")
        if response.get("errno", 0) != 0:
            raise LongshiConnectionError(
                f"Device identification failed: {response.get('errno')}"
            )

    async def _wait_for_device_login(self, websocket: Any) -> dict[str, Any]:
        """Wake and retry device login like the vendor SDK."""
        retry_interval = 1.0
        attempts = max(2, int(self.timeout // retry_interval))
        for _ in range(attempts):
            await self._send_to_device(websocket, {"req": "login"})
            try:
                while True:
                    raw = await asyncio.wait_for(websocket.recv(), retry_interval)
                    message = self._decode_device_message(json.loads(raw))
                    if message and message.get("res") == "login":
                        return message
            except asyncio.TimeoutError:
                continue
        raise LongshiConnectionError(f"Device {self.device.cid} did not answer login")
