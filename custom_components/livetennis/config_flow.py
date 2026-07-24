"""Config and options flow for the Live Tennis integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_API_KEY, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import LiveTennisApiClient, LiveTennisAuthError, LiveTennisRateLimitError
from .const import (
    CONF_PER_MATCH_SENSORS,
    CONF_TOURS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    TOURS,
)

_TOUR_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        options=list(TOURS),
        multiple=True,
        mode=SelectSelectorMode.LIST,
        translation_key="tours",
    )
)

_SCAN_INTERVAL_SELECTOR = NumberSelector(
    NumberSelectorConfig(
        min=MIN_SCAN_INTERVAL,
        max=MAX_SCAN_INTERVAL,
        step=10,
        unit_of_measurement="s",
        mode=NumberSelectorMode.BOX,
    )
)


async def _validate_key(hass, api_key: str) -> str | None:
    """Return an error key, or None if the key is valid."""
    session = async_get_clientsession(hass)
    client = LiveTennisApiClient(session, api_key)
    try:
        await client.async_validate_key()
    except LiveTennisAuthError:
        return "invalid_auth"
    except LiveTennisRateLimitError:
        return "rate_limited"
    except Exception:  # noqa: BLE001 - map any transport failure to cannot_connect
        return "cannot_connect"
    return None


class LiveTennisConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial configuration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            error = await _validate_key(self.hass, user_input[CONF_API_KEY].strip())
            if error:
                errors["base"] = error
            else:
                data = {CONF_API_KEY: user_input[CONF_API_KEY].strip()}
                options = {
                    CONF_TOURS: user_input.get(CONF_TOURS, []),
                    CONF_SCAN_INTERVAL: int(
                        user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                    ),
                    CONF_PER_MATCH_SENSORS: user_input.get(
                        CONF_PER_MATCH_SENSORS, True
                    ),
                }
                return self.async_create_entry(
                    title="Live Tennis", data=data, options=options
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
                vol.Optional(CONF_TOURS, default=[]): _TOUR_SELECTOR,
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                ): _SCAN_INTERVAL_SELECTOR,
                vol.Optional(
                    CONF_PER_MATCH_SENSORS, default=True
                ): BooleanSelector(),
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return LiveTennisOptionsFlow()


class LiveTennisOptionsFlow(OptionsFlow):
    """Allow changing tours, poll interval, and per-match sensors."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                data={
                    CONF_TOURS: user_input.get(CONF_TOURS, []),
                    CONF_SCAN_INTERVAL: int(
                        user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                    ),
                    CONF_PER_MATCH_SENSORS: user_input.get(
                        CONF_PER_MATCH_SENSORS, True
                    ),
                }
            )

        current = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_TOURS, default=current.get(CONF_TOURS, [])
                ): _TOUR_SELECTOR,
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=current.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): _SCAN_INTERVAL_SELECTOR,
                vol.Optional(
                    CONF_PER_MATCH_SENSORS,
                    default=current.get(CONF_PER_MATCH_SENSORS, True),
                ): BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
