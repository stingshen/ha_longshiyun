"""Binary sensors for Longshi Cloud."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .entity import LongshiEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        LongshiConnectivityEntity(coordinator, cid) for cid in coordinator.devices
    )


class LongshiConnectivityEntity(LongshiEntity, BinarySensorEntity):
    """Device connectivity."""

    _attr_name = "Connectivity"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator, cid: str):
        super().__init__(coordinator, cid)
        self._attr_unique_id = f"{cid}_connectivity"

    @property
    def is_on(self) -> bool:
        return bool(self.device_data["online"])

    @property
    def available(self) -> bool:
        return True

    @property
    def extra_state_attributes(self):
        return {
            "control_available": self.device_data["available"],
            "gateway_alive_date": self.device_data.get("gateway_alive_date"),
            "error": self.device_data.get("error"),
        }
