"""Integration test: full config-entry setup through Home Assistant.

Uses pytest-homeassistant-custom-component's aioclient_mock to serve a captured
real API payload (tests/fixtures/live_matches.json), so it runs deterministically
in CI with no API key and no network.
"""

import json
from pathlib import Path

from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_API_KEY, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant

from custom_components.livetennis.api import DEFAULT_BASE_URL
from custom_components.livetennis.const import (
    CONF_PER_MATCH_SENSORS,
    CONF_TOURS,
    DOMAIN,
)

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "live_matches.json").read_text()
)


def _mk_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="Live Tennis",
        data={CONF_API_KEY: "test-key"},
        options={
            CONF_TOURS: [],
            CONF_SCAN_INTERVAL: 120,
            CONF_PER_MATCH_SENSORS: True,
        },
    )


async def test_setup_creates_count_and_match_sensors(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(f"{DEFAULT_BASE_URL}/matches", json=FIXTURE)

    entry = _mk_entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED

    n = len(FIXTURE["data"])
    count = hass.states.get("sensor.live_matches")
    assert count is not None
    assert int(count.state) == n
    assert len(count.attributes["match_ids"]) == n

    match_sensors = [
        s
        for s in hass.states.async_all("sensor")
        if s.entity_id != "sensor.live_matches"
    ]
    assert len(match_sensors) == n

    # Every per-match sensor has a non-empty, non-error state and expected attrs.
    for s in match_sensors:
        assert s.state not in ("unavailable", "unknown", "")
        assert "player_1" in s.attributes
        assert "player_2" in s.attributes
        assert "tournament" in s.attributes

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_invalid_auth_raises_config_flow_error(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A 401 during setup must not silently succeed."""
    aioclient_mock.get(f"{DEFAULT_BASE_URL}/matches", status=401, json={"error": "unauthorized"})

    entry = _mk_entry()
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # 401 -> ConfigEntryAuthFailed -> entry enters SETUP_ERROR (reauth), not LOADED.
    assert entry.state is not ConfigEntryState.LOADED


async def test_per_match_sensors_disabled(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(f"{DEFAULT_BASE_URL}/matches", json=FIXTURE)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Live Tennis",
        data={CONF_API_KEY: "test-key"},
        options={CONF_TOURS: [], CONF_SCAN_INTERVAL: 120, CONF_PER_MATCH_SENSORS: False},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Only the count sensor should exist.
    sensors = hass.states.async_all("sensor")
    assert len(sensors) == 1
    assert sensors[0].entity_id == "sensor.live_matches"
