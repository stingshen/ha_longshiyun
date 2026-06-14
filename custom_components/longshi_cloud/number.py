"""Number controls for Longshi Cloud."""

from homeassistant.components.number import NumberEntity, NumberMode
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
                LongshiRecordNumber(
                    coordinator, cid, "sens", "Recording sensitivity", "setRecordSens"
                ),
                LongshiRecordNumber(
                    coordinator, cid, "vol", "Recording volume", "setRecordVolume"
                ),
            ]
        )
    async_add_entities(entities)


class LongshiRecordNumber(LongshiEntity, NumberEntity):
    """Recording numeric control."""

    _attr_mode = NumberMode.SLIDER
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1

    def __init__(self, coordinator, cid: str, key: str, name: str, request: str):
        super().__init__(coordinator, cid)
        self.key = key
        self.request = request
        self._attr_name = name
        self._attr_unique_id = f"{cid}_{key}"

    @property
    def native_value(self):
        return self.record_config().get(self.key)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_command(
            self.cid, {"req": self.request, self.key: int(value)}
        )
