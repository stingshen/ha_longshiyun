"""Data coordinator for Longshi Cloud."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import LongshiCloudClient, LongshiDevice, LongshiDeviceClient
from .const import DEFAULT_UPDATE_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class LongshiCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate cloud discovery and device polling."""

    def __init__(
        self, hass: HomeAssistant, cloud: LongshiCloudClient, zone: int | None
    ):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_UPDATE_INTERVAL),
        )
        self.cloud = cloud
        self.zone = zone
        self.devices: dict[str, LongshiDevice] = {}
        self._record_mode_tasks: dict[str, asyncio.Task[None]] = {}
        self._record_mode_locks: dict[str, asyncio.Lock] = {}
        self._record_mode_setting: dict[str, dict[str, Any]] = {}

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            devices = await self.cloud.async_list_devices()
        except Exception as exc:
            raise UpdateFailed(f"Unable to update Longshi Cloud: {exc}") from exc

        self.devices = {device.cid: device for device in devices}
        results = await asyncio.gather(
            *(self._async_update_device(device) for device in devices),
            return_exceptions=False,
        )
        return {device.cid: result for device, result in zip(devices, results)}

    async def _async_update_device(self, device: LongshiDevice) -> dict[str, Any]:
        data: dict[str, Any] = {
            "available": False,
            "online": False,
            "device": device,
            "responses": {},
        }
        client = LongshiDeviceClient(self.cloud, device, self.zone)
        try:
            responses = await client.async_run(
                [
                    {"req": "getIotModel"},
                    {"req": "getAllStatus"},
                    {"req": "getUsrConfig"},
                    {"req": "getRecordMode"},
                    {"req": "getRecordSens"},
                    {"req": "getRecordVolume"},
                    {"req": "getRecordDate"},
                ]
            )
            data["available"] = True
            data["responses"] = {response["res"]: response for response in responses}
        except Exception as exc:
            data["error"] = str(exc)
            _LOGGER.debug("Device %s unavailable: %s", device.cid, exc)
        data["online"] = client.gateway_online
        data["gateway_alive_date"] = client.gateway_alive_date
        return data

    async def async_command(self, cid: str, request: dict[str, Any]) -> dict[str, Any]:
        """Send a command and update its authoritative response."""
        device = self.devices[cid]
        client = LongshiDeviceClient(self.cloud, device, self.zone)
        verify_by_request = {
            "setRecordMode": ("getRecordMode", "mode"),
            "setRecordSens": ("getRecordSens", "sens"),
            "setRecordVolume": ("getRecordVolume", "vol"),
        }
        verify_request, field = verify_by_request[request["req"]]
        response = await client.async_set_and_verify(request, verify_request, field)
        self.data[cid]["available"] = True
        self.data[cid]["responses"][verify_request] = response
        self.async_update_listeners()
        return response

    def record_mode_setting(self, cid: str) -> dict[str, Any]:
        """Return the current recording mode setting state."""
        return self._record_mode_setting.get(
            cid,
            {
                "state": "idle",
                "target": None,
                "error": None,
                "previous_target_cancelled": None,
            },
        )

    async def async_set_record_mode(self, cid: str, mode: int, target: str) -> None:
        """Cancel an older mode setting task and apply the latest target."""
        lock = self._record_mode_locks.setdefault(cid, asyncio.Lock())
        async with lock:
            previous_task = self._record_mode_tasks.get(cid)
            previous_target = None
            if previous_task and not previous_task.done():
                previous_target = self.record_mode_setting(cid).get("target")
                self._record_mode_tasks.pop(cid, None)
                self._set_record_mode_setting(
                    cid,
                    state="setting",
                    target=target,
                    previous_target_cancelled=previous_target,
                )
                previous_task.cancel()
                with suppress(asyncio.CancelledError):
                    await previous_task

            if previous_target is None:
                self._set_record_mode_setting(cid, state="setting", target=target)
            task = self.hass.async_create_task(
                self._async_apply_record_mode(cid, mode, target),
                f"Set {cid} recording mode to {target}",
            )
            self._record_mode_tasks[cid] = task
        try:
            await task
        except asyncio.CancelledError:
            if self._record_mode_tasks.get(cid) is task:
                raise
            # A newer user selection superseded this task.
            return
        finally:
            if self._record_mode_tasks.get(cid) is task and task.done():
                self._record_mode_tasks.pop(cid, None)

    async def _async_apply_record_mode(self, cid: str, mode: int, target: str) -> None:
        previous_target = self.record_mode_setting(cid).get("previous_target_cancelled")
        try:
            await self.async_command(cid, {"req": "setRecordMode", "mode": mode})
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._set_record_mode_setting(
                cid,
                state="failed",
                target=target,
                error=str(exc),
                previous_target_cancelled=previous_target,
            )
            raise
        else:
            self._set_record_mode_setting(
                cid,
                state="succeeded",
                target=target,
                previous_target_cancelled=previous_target,
            )

    def _set_record_mode_setting(
        self,
        cid: str,
        *,
        state: str,
        target: str | None,
        error: str | None = None,
        previous_target_cancelled: str | None = None,
    ) -> None:
        self._record_mode_setting[cid] = {
            "state": state,
            "target": target,
            "error": error,
            "previous_target_cancelled": previous_target_cancelled,
        }
        self.async_update_listeners()
