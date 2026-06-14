"""Longshi Cloud integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .api import LongshiCloudClient
from .const import (
    CONF_REGION,
    CONF_ZONE,
    DEFAULT_REGION,
    DEFAULT_TIMEOUT,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import LongshiCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Longshi Cloud from a config entry."""
    cloud = LongshiCloudClient(
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        DEFAULT_TIMEOUT,
        entry.data.get(CONF_REGION, DEFAULT_REGION),
    )
    coordinator = LongshiCoordinator(hass, cloud, entry.data.get(CONF_ZONE))
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded
