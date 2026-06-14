"""Sensors for Longshi Cloud."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .entity import LongshiEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for cid in coordinator.devices:
        entities.extend(
            [
                LongshiStatusEntity(coordinator, cid),
                LongshiScheduleEntity(coordinator, cid),
                LongshiRecordModeSettingEntity(coordinator, cid),
            ]
        )
    async_add_entities(entities)


class LongshiStatusEntity(LongshiEntity, SensorEntity):
    """Combined device status sensor."""

    _attr_name = "Status"

    def __init__(self, coordinator, cid: str):
        super().__init__(coordinator, cid)
        self._attr_unique_id = f"{cid}_status"

    @property
    def native_value(self):
        return "online" if self.device_data["online"] else "offline"

    @property
    def available(self) -> bool:
        return True

    @property
    def extra_state_attributes(self):
        return {
            "model": self.response("getIotModel").get("value"),
            "status": self.response("getAllStatus").get("value"),
            "config": self.response("getUsrConfig").get("value"),
            "control_available": self.device_data["available"],
            "gateway_alive_date": self.device_data.get("gateway_alive_date"),
            "error": self.device_data.get("error"),
        }


class LongshiScheduleEntity(LongshiEntity, SensorEntity):
    """Recording schedule sensor."""

    _attr_name = "Recording schedule"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator, cid: str):
        super().__init__(coordinator, cid)
        self._attr_unique_id = f"{cid}_recording_schedule"

    @property
    def native_value(self):
        value = self.response("getRecordDate").get("value")
        if value is None:
            value = self.record_config().get("date")
        return len(value) if isinstance(value, list) else 0

    @property
    def extra_state_attributes(self):
        value = self.response("getRecordDate").get("value")
        return {
            "schedule": value if value is not None else self.record_config().get("date")
        }


class LongshiRecordModeSettingEntity(LongshiEntity, SensorEntity):
    """Recording mode setting progress sensor."""

    _attr_name = "Recording mode setting state"
    _attr_icon = "mdi:cog-sync"

    def __init__(self, coordinator, cid: str):
        super().__init__(coordinator, cid)
        self._attr_unique_id = f"{cid}_recording_mode_setting_state"

    @property
    def native_value(self):
        return self.coordinator.record_mode_setting(self.cid)["state"]

    @property
    def available(self) -> bool:
        return True

    @property
    def extra_state_attributes(self):
        setting = self.coordinator.record_mode_setting(self.cid)
        return {
            "target": setting["target"],
            "error": setting["error"],
            "previous_target_cancelled": setting["previous_target_cancelled"],
        }
