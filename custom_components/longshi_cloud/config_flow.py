"""Config flow for Longshi Cloud."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from .api import LongshiAuthError, LongshiCloudClient, LongshiConnectionError
from .const import CONF_REGION, CONF_ZONE, DEFAULT_REGION, DEFAULT_TIMEOUT, DOMAIN


class LongshiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Longshi Cloud config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            cloud = LongshiCloudClient(
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                DEFAULT_TIMEOUT,
                user_input[CONF_REGION],
            )
            try:
                await cloud.async_list_devices()
            except LongshiAuthError:
                errors["base"] = "invalid_auth"
            except LongshiConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_input[CONF_USERNAME].lower())
                self._abort_if_unique_id_configured()
                title = user_input[CONF_USERNAME]
                return self.async_create_entry(
                    title=title,
                    data={
                        **user_input,
                        CONF_ZONE: user_input.get(CONF_ZONE) or cloud.zone,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_REGION, default=DEFAULT_REGION): vol.In(
                    ["auto", "cn", "asia", "us"]
                ),
                vol.Optional(CONF_ZONE): vol.Coerce(int),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
