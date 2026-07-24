"""Thin async client for the Live Tennis API.

This module deliberately has NO Home Assistant imports and NO relative imports
so it can be imported and exercised standalone (e.g. against the live API in a
test harness) as well as from inside the integration.
"""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

DEFAULT_BASE_URL = "https://api.livetennisapi.com/api/public/v1"
DEFAULT_TIMEOUT = 30


class LiveTennisApiError(Exception):
    """Base error for the Live Tennis API client."""


class LiveTennisAuthError(LiveTennisApiError):
    """Raised on 401 - missing, unknown, or disabled credentials."""


class LiveTennisRateLimitError(LiveTennisApiError):
    """Raised on 429 - rate limit exceeded. Carries Retry-After seconds."""

    def __init__(self, message: str, retry_after: int | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class LiveTennisApiClient:
    """Minimal read-only client covering the FREE-tier endpoints we need."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
    ) -> None:
        self._session = session
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    @property
    def _headers(self) -> dict[str, str]:
        # The API accepts either `X-API-Key: <key>` or `Authorization: Bearer`.
        # We use the dedicated header to avoid any Authorization-stripping proxies.
        return {"X-API-Key": self._api_key, "Accept": "application/json"}

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self._base_url}/{path.lstrip('/')}"
        try:
            async with self._session.get(
                url,
                headers=self._headers,
                params=params or {},
                timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT),
            ) as resp:
                if resp.status == 401:
                    raise LiveTennisAuthError("Invalid or disabled API key (401)")
                if resp.status == 429:
                    retry_after = _parse_retry_after(resp.headers.get("Retry-After"))
                    raise LiveTennisRateLimitError(
                        "Rate limit exceeded (429)", retry_after=retry_after
                    )
                if resp.status >= 400:
                    body = await resp.text()
                    raise LiveTennisApiError(
                        f"HTTP {resp.status} from {path}: {body[:200]}"
                    )
                return await resp.json()
        except aiohttp.ClientError as err:
            raise LiveTennisApiError(f"Connection error to {path}: {err}") from err
        except asyncio.TimeoutError as err:
            raise LiveTennisApiError(f"Timeout contacting {path}") from err

    async def async_validate_key(self) -> None:
        """Cheap authenticated call used to validate a key. Raises on failure."""
        await self._get("/matches", {"status": "live", "limit": 1})

    async def async_get_matches(
        self, status: str = "live", tour: str | None = None, limit: int = 200
    ) -> list[dict[str, Any]]:
        """Return the `data` list for /matches, or [] if absent."""
        params: dict[str, Any] = {"status": status, "limit": limit}
        if tour:
            params["tour"] = tour
        payload = await self._get("/matches", params)
        if isinstance(payload, dict):
            data = payload.get("data")
            if isinstance(data, list):
                return data
        return []

    async def async_get_live_matches(
        self, tours: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Return live matches, merged and de-duplicated across selected tours.

        With no tours (or an empty list) a single unfiltered request is made.
        Otherwise one request per selected tour is made and the results are
        merged by match id (a match cannot appear under two filter tours, but we
        de-dupe defensively).
        """
        if not tours:
            return await self.async_get_matches(status="live")

        merged: dict[int, dict[str, Any]] = {}
        for tour in tours:
            for match in await self.async_get_matches(status="live", tour=tour):
                match_id = match.get("id")
                if isinstance(match_id, int):
                    merged[match_id] = match
        return list(merged.values())


def _parse_retry_after(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
