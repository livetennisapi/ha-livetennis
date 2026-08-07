"""DataUpdateCoordinator for the Live Tennis integration."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    LiveTennisAbuseThrottledError,
    LiveTennisApiClient,
    LiveTennisApiError,
    LiveTennisAuthError,
    LiveTennisRateLimitError,
)
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

ABUSE_ISSUE_ID = "abuse_throttled"
# The abuse block is typically 24 h; never sleep longer than that even if the
# server hands us a bogus retry_at_epoch.
MAX_ABUSE_BACKOFF = 24 * 3600


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
        self._scan_interval = scan_interval
        self._abuse_throttled = False

    async def _async_update_data(self) -> dict[int, dict[str, Any]]:
        try:
            matches = await self._client.async_get_live_matches(self._tours)
        except LiveTennisAuthError as err:
            # Surface as reauth rather than a transient failure.
            raise ConfigEntryAuthFailed(str(err)) from err
        except LiveTennisAbuseThrottledError as err:
            retry_in = self._abuse_backoff_seconds(err)
            retry_at = datetime.now(timezone.utc) + timedelta(seconds=retry_in)
            self._abuse_throttled = True
            # Back off: the next scheduled refresh waits until the block lifts.
            self.update_interval = timedelta(seconds=retry_in)
            _LOGGER.warning(
                "The Live Tennis API has abuse-throttled this API key "
                "(chronic over-quota use, usually a broken retry loop on some "
                "client of this key). Polling paused until %s (%d s). "
                "Check every consumer of this key and its request budget",
                retry_at.isoformat(timespec="seconds"),
                retry_in,
            )
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                ABUSE_ISSUE_ID,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key=ABUSE_ISSUE_ID,
                translation_placeholders={
                    "retry_at": retry_at.isoformat(timespec="seconds"),
                },
                learn_more_url="https://docs.livetennisapi.com",
            )
            raise UpdateFailed(
                f"API key abuse-throttled until {retry_at.isoformat(timespec='seconds')}"
            ) from err
        except LiveTennisRateLimitError as err:
            raise UpdateFailed(str(err)) from err
        except LiveTennisApiError as err:
            raise UpdateFailed(str(err)) from err

        if self._abuse_throttled:
            # Block lifted: restore the configured cadence and clear the repair.
            self._abuse_throttled = False
            self.update_interval = timedelta(seconds=self._scan_interval)
            ir.async_delete_issue(self.hass, DOMAIN, ABUSE_ISSUE_ID)
            _LOGGER.info(
                "Live Tennis API abuse throttle lifted; resuming polling every %d s",
                self._scan_interval,
            )

        result: dict[int, dict[str, Any]] = {}
        for match in matches:
            match_id = match.get("id")
            if isinstance(match_id, int):
                result[match_id] = match
        return result

    def _abuse_backoff_seconds(self, err: LiveTennisAbuseThrottledError) -> int:
        """Seconds to wait before the next poll after an abuse_throttled 429."""
        candidates = [self._scan_interval]
        if err.retry_after is not None:
            candidates.append(err.retry_after)
        if err.retry_at_epoch is not None:
            candidates.append(int(err.retry_at_epoch - time.time()))
        return min(max(candidates), MAX_ABUSE_BACKOFF)
