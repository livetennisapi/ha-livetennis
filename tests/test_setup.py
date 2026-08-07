"""Integration test: full config-entry setup through Home Assistant.

Uses pytest-homeassistant-custom-component's aioclient_mock to serve a captured
real API payload (tests/fixtures/live_matches.json), so it runs deterministically
in CI with no API key and no network.
"""

from datetime import timedelta
import json
from pathlib import Path
import time

from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.const import CONF_API_KEY, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir

from custom_components.livetennis.api import DEFAULT_BASE_URL
from custom_components.livetennis.const import (
    CONF_PER_MATCH_SENSORS,
    CONF_TOURS,
    DOMAIN,
)
from custom_components.livetennis.coordinator import ABUSE_ISSUE_ID

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
    """A 401 during setup must start a reauth flow, not silently succeed."""
    aioclient_mock.get(f"{DEFAULT_BASE_URL}/matches", status=401, json={"error": "unauthorized"})

    entry = _mk_entry()
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # 401 -> ConfigEntryAuthFailed -> entry enters SETUP_ERROR (reauth), not LOADED.
    assert entry.state is not ConfigEntryState.LOADED

    # A reauth flow must be in progress, showing the reauth_confirm form.
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert len(flows) == 1
    assert flows[0]["context"]["source"] == SOURCE_REAUTH
    assert flows[0]["step_id"] == "reauth_confirm"

    # Submitting a working key completes the reauth and reloads the entry.
    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{DEFAULT_BASE_URL}/matches", json=FIXTURE)
    result = await hass.config_entries.flow.async_configure(
        flows[0]["flow_id"], {CONF_API_KEY: "new-key"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_API_KEY] == "new-key"
    assert entry.state is ConfigEntryState.LOADED


async def test_reauth_rejects_bad_replacement_key(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A still-invalid key submitted during reauth re-shows the form."""
    aioclient_mock.get(f"{DEFAULT_BASE_URL}/matches", status=401, json={"error": "unauthorized"})

    entry = _mk_entry()
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert len(flows) == 1

    result = await hass.config_entries.flow.async_configure(
        flows[0]["flow_id"], {CONF_API_KEY: "still-bad"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}
    assert entry.data[CONF_API_KEY] == "test-key"


async def test_abuse_throttled_backs_off_and_creates_repair(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """429 abuse_throttled pauses polling until retry_at and raises a repair."""
    aioclient_mock.get(f"{DEFAULT_BASE_URL}/matches", json=FIXTURE)

    entry = _mk_entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN][entry.entry_id]
    retry_at = int(time.time()) + 4 * 3600

    aioclient_mock.clear_requests()
    aioclient_mock.get(
        f"{DEFAULT_BASE_URL}/matches",
        status=429,
        json={"error": "abuse_throttled", "retry_at_epoch": retry_at},
        headers={"Retry-After": "14400"},
    )
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert coordinator.last_update_success is False
    # Next poll is deferred until (about) retry_at, not the 120 s scan interval.
    assert coordinator.update_interval >= timedelta(hours=3, minutes=55)
    issue = ir.async_get(hass).async_get_issue(DOMAIN, ABUSE_ISSUE_ID)
    assert issue is not None
    assert issue.translation_key == ABUSE_ISSUE_ID

    # Once the API serves data again, cadence is restored and the repair clears.
    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{DEFAULT_BASE_URL}/matches", json=FIXTURE)
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert coordinator.last_update_success is True
    assert coordinator.update_interval == timedelta(seconds=120)
    assert ir.async_get(hass).async_get_issue(DOMAIN, ABUSE_ISSUE_ID) is None


async def test_plain_rate_limit_does_not_create_repair(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """An ordinary minute-window 429 is a transient failure, no repair issue."""
    aioclient_mock.get(f"{DEFAULT_BASE_URL}/matches", json=FIXTURE)

    entry = _mk_entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN][entry.entry_id]

    aioclient_mock.clear_requests()
    aioclient_mock.get(
        f"{DEFAULT_BASE_URL}/matches",
        status=429,
        json={"error": "rate_limited", "scope": "minute"},
        headers={"Retry-After": "12"},
    )
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert coordinator.last_update_success is False
    assert coordinator.update_interval == timedelta(seconds=120)
    assert ir.async_get(hass).async_get_issue(DOMAIN, ABUSE_ISSUE_ID) is None


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
