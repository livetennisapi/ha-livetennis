"""Constants for the Live Tennis integration."""

from __future__ import annotations

DOMAIN = "livetennis"

# Shown in the config flow as description placeholders: hassfest rejects
# literal URLs inside translated strings.
SIGNUP_URL = "https://livetennisapi.com/subscribe/free"
ACCOUNT_URL = "https://livetennisapi.com/account"

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
# tour filter is set). The free tier allows 30 requests/minute AND 100
# requests/day — the *daily* cap is the binding one:
#   86400 s / 900 s = 96 cycles/day
#   0-1 tours -> 96/day  (fits the free tier at the 900 s default)
#   2 tours   -> 192/day (needs >= 1800 s: 96/day)
#   3 tours   -> 288/day (needs >= 2700 s: 96/day)
#   4 tours   -> 384/day (needs >= 3600 s: 96/day)
#   5 tours   -> 480/day (does NOT fit free even at the 3600 s max: 120/day —
#                needs the Basic tier)
# The default is 900 s so the common setups (no filter, or one tour) fit the
# free tier's 100/day with the interval left alone; the README documents
# per-tour intervals for the rest. Faster polling (e.g. the old 120 s default,
# 720/day) needs the Basic tier (1,000/day).
DEFAULT_SCAN_INTERVAL = 900
# Floor chosen for the per-minute limit (5 per-tour requests / 60 s = 5
# req/min, well within 30). NOTE: on a free key, 60 s wildly exceeds the
# 100/day cap even with a single tour (1,440/day); even Basic (1,000/day)
# needs >= 90 s for one tour — see the README quota table.
MIN_SCAN_INTERVAL = 60
MAX_SCAN_INTERVAL = 3600
