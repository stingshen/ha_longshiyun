"""Constants for the Longshi Cloud integration."""

from __future__ import annotations

DOMAIN = "longshi_cloud"
CONF_REGION = "region"
CONF_ZONE = "zone"
CONF_REFRESH_INTERVAL = "refresh_interval"

DEFAULT_REGION = "auto"
DEFAULT_REFRESH_INTERVAL = 0
DEFAULT_TIMEOUT = 12

PLATFORMS = ["binary_sensor", "sensor", "select", "number", "button"]

RECORD_MODES = {
    "0": "All Day",
    "1": "Event",
    "2": "Schedule",
    "3": "Off",
}
RECORD_MODE_VALUES = {label: int(value) for value, label in RECORD_MODES.items()}
