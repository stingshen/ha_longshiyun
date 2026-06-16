"""Button entities for Longshi Cloud."""

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .entity import LongshiEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        LongshiForceRefreshButton(coordinator, cid) for cid in coordinator.devices
    )


class LongshiForceRefreshButton(LongshiEntity, ButtonEntity):
    """Force a device data refresh."""

    _attr_name = "Force refresh"
    _attr_icon = "mdi:refresh"

    def __init__(self, coordinator, cid: str):
        super().__init__(coordinator, cid)
        self._attr_unique_id = f"{cid}_force_refresh"

    @property
    def available(self) -> bool:
        return True

    async def async_press(self) -> None:
        """Refresh Longshi Cloud data on demand."""
        await self.coordinator.async_request_refresh()
