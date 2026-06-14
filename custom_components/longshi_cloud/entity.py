"""Base entities for Longshi Cloud."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import LongshiCoordinator


class LongshiEntity(CoordinatorEntity[LongshiCoordinator]):
    """Base Longshi Cloud entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: LongshiCoordinator, cid: str):
        super().__init__(coordinator)
        self.cid = cid

    @property
    def device_data(self) -> dict[str, Any]:
        return self.coordinator.data[self.cid]

    @property
    def available(self) -> bool:
        return bool(self.device_data["available"])

    @property
    def device_info(self) -> DeviceInfo:
        device = self.device_data["device"]
        return DeviceInfo(
            identifiers={(DOMAIN, self.cid)},
            name=device.name,
            manufacturer="Longshi Cloud",
            model=str(device.info.get("feature", "Recording device")),
            serial_number=self.cid,
        )

    def response(self, name: str) -> dict[str, Any]:
        return self.device_data["responses"].get(name, {})

    def record_config(self) -> dict[str, Any]:
        config = self.response("getUsrConfig").get("value", {})
        record = dict(config.get("record", {})) if isinstance(config, dict) else {}
        mode = self.response("getRecordMode").get("value", {}).get("mode")
        sensitivity = self.response("getRecordSens").get("value")
        volume = self.response("getRecordVolume").get("value")
        if mode is not None:
            record["mode"] = mode
        if sensitivity is not None:
            record["sens"] = sensitivity
        if volume is not None:
            record["vol"] = volume
        return record
