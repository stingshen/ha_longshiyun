"""Select entities for Longshi Cloud."""

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, RECORD_MODES, RECORD_MODE_VALUES
from .entity import LongshiEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        LongshiRecordModeEntity(coordinator, cid) for cid in coordinator.devices
    )


class LongshiRecordModeEntity(LongshiEntity, SelectEntity):
    """Recording mode control."""

    _attr_name = "Recording mode"
    _attr_icon = "mdi:record-rec"
    _attr_options = list(RECORD_MODE_VALUES)

    def __init__(self, coordinator, cid: str):
        super().__init__(coordinator, cid)
        self._attr_unique_id = f"{cid}_recording_mode"

    @property
    def current_option(self):
        mode = self.record_config().get("mode")
        return RECORD_MODES.get(str(mode))

    @property
    def extra_state_attributes(self):
        setting = self.coordinator.record_mode_setting(self.cid)
        return {
            "setting_state": setting["state"],
            "setting_target": setting["target"],
        }

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_record_mode(
            self.cid, RECORD_MODE_VALUES[option], option
        )
