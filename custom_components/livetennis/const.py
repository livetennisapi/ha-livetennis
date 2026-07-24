"""Constants for the Live Tennis integration."""

from __future__ import annotations

DOMAIN = "livetennis"

# Shown in the config flow as a description placeholder: hassfest rejects
# literal URLs inside translated strings.
SIGNUP_URL = "https://livetennisapi.com/subscribe/free"

# Config / options keys
CONF_API_KEY = "api_key"
CONF_TOURS = "tours"
CONF_PER_MATCH_SENSORS = "per_match_sensors"
# CONF_SCAN_INTERVAL is reused from homeassistant.const

# Tour filter vocabulary accepted by the API's ?tour= parameter.
# NOTE: this is the *filter* vocabulary, which is grouped and distinct from a
# player/fixture record's own granular `tour` string (see openapi.yaml).
TOURS: tuple[str, ...] = ("atp", "wta", "challenger", "itf", "juniors")

# Polling.
# The free tier allows 30 requests/minute. A cycle issues at most one request
# per selected tour (or a single request when no tour filter is set), so the
# default of 120s stays far below the limit even with every tour selected.
DEFAULT_SCAN_INTERVAL = 120
# Floor chosen so that even 5 per-tour requests per cycle (5 req / 60 s) stay
# comfortably within 30 req/min.
MIN_SCAN_INTERVAL = 60
MAX_SCAN_INTERVAL = 3600
