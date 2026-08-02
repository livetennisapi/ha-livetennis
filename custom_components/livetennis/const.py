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
# A cycle issues one request per selected tour (or a single request when no
# tour filter is set). The free tier allows 30 requests/minute AND 1,000
# requests/day — the *daily* cap is the binding one:
#   86400 s / 120 s = 720 cycles/day
#   0-1 tours -> 720/day   (fits the free tier at the 120 s default)
#   2 tours   -> 1,440/day (needs >= 180 s: 960/day)
#   3 tours   -> 2,160/day (needs >= 300 s: 864/day)
#   4 tours   -> 2,880/day (needs >= 360 s: 960/day)
#   5 tours   -> 3,600/day (needs >= 450 s: 960/day)
# The default stays 120 s because it is correct for the common setups (no
# filter, or one tour); the README documents per-tour intervals for the rest.
DEFAULT_SCAN_INTERVAL = 120
# Floor chosen for the per-minute limit (5 per-tour requests / 60 s = 5
# req/min, well within 30). NOTE: on a free key, 60 s already exceeds the
# daily cap even with a single tour (1,440/day) — see the README quota table.
MIN_SCAN_INTERVAL = 60
MAX_SCAN_INTERVAL = 3600
