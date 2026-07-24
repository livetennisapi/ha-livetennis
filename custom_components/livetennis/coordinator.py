"""DataUpdateCoordinator for the Live Tennis integration."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    LiveTennisApiClient,
    LiveTennisApiError,
    LiveTennisAuthError,
    LiveTennisRateLimitError,
)
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class LiveTennisDataUpdateCoordinator(DataUpdateCoordinator[dict[int, dict[str, Any]]]):
    """Polls live matches and exposes them keyed by match id."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: LiveTennisApiClient,
        tours: list[str],
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self._client = client
        self._tours = tours

    async def _async_update_data(self) -> dict[int, dict[str, Any]]:
        try:
            matches = await self._client.async_get_live_matches(self._tours)
        except LiveTennisAuthError as err:
            # Surface as reauth rather than a transient failure.
            raise ConfigEntryAuthFailed(str(err)) from err
        except LiveTennisRateLimitError as err:
            raise UpdateFailed(str(err)) from err
        except LiveTennisApiError as err:
            raise UpdateFailed(str(err)) from err

        result: dict[int, dict[str, Any]] = {}
        for match in matches:
            match_id = match.get("id")
            if isinstance(match_id, int):
                result[match_id] = match
        return result
