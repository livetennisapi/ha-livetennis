"""Sensor platform for the Live Tennis integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_PER_MATCH_SENSORS, DOMAIN
from .coordinator import LiveTennisDataUpdateCoordinator
from .helpers import format_state, match_attributes, match_title


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the live-matches count sensor and dynamic per-match sensors."""
    coordinator: LiveTennisDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([LiveMatchesCountSensor(coordinator, entry)])

    per_match = {**entry.data, **entry.options}.get(CONF_PER_MATCH_SENSORS, True)
    if not per_match:
        return

    known: set[int] = set()

    @callback
    def _add_new_matches() -> None:
        data = coordinator.data or {}
        new_ids = [mid for mid in data if mid not in known]
        if not new_ids:
            return
        known.update(new_ids)
        async_add_entities(
            LiveMatchSensor(coordinator, entry, match_id) for match_id in new_ids
        )

    _add_new_matches()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_matches))


class LiveMatchesCountSensor(
    CoordinatorEntity[LiveTennisDataUpdateCoordinator], SensorEntity
):
    """Number of currently live matches."""

    _attr_has_entity_name = True
    _attr_name = "Live matches"
    _attr_icon = "mdi:tennis"
    _attr_native_unit_of_measurement = "matches"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: LiveTennisDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_live_matches_count"

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data or {})

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        return {
            "match_ids": list(data.keys()),
            "tournaments": sorted(
                {m.get("tournament") for m in data.values() if m.get("tournament")}
            ),
        }


class LiveMatchSensor(
    CoordinatorEntity[LiveTennisDataUpdateCoordinator], SensorEntity
):
    """One sensor per live match; state is a compact score."""

    _attr_has_entity_name = False
    _attr_icon = "mdi:tennis-ball"

    def __init__(
        self,
        coordinator: LiveTennisDataUpdateCoordinator,
        entry: ConfigEntry,
        match_id: int,
    ) -> None:
        super().__init__(coordinator)
        self._match_id = match_id
        self._attr_unique_id = f"{entry.entry_id}_match_{match_id}"
        match = (coordinator.data or {}).get(match_id, {})
        self._attr_name = f"Tennis: {match_title(match)}" if match else f"Tennis match {match_id}"

    @property
    def _match(self) -> dict[str, Any] | None:
        return (self.coordinator.data or {}).get(self._match_id)

    @property
    def available(self) -> bool:
        # Unavailable once the match drops out of the live feed (finished/removed).
        return super().available and self._match is not None

    @property
    def native_value(self) -> str | None:
        match = self._match
        if match is None:
            return None
        return format_state(match)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        match = self._match
        if match is None:
            return None
        return match_attributes(match)
