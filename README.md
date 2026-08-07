# Live Tennis for Home Assistant

A [HACS](https://hacs.xyz)-installable custom integration that surfaces **live
tennis scores** across ATP, WTA, Challenger, ITF and juniors in Home Assistant,
powered by the [Live Tennis API](https://livetennisapi.com).

[![Validate](https://github.com/livetennisapi/ha-livetennis/actions/workflows/validate.yml/badge.svg)](https://github.com/livetennisapi/ha-livetennis/actions/workflows/validate.yml)
[![CI](https://github.com/livetennisapi/ha-livetennis/actions/workflows/ci.yml/badge.svg)](https://github.com/livetennisapi/ha-livetennis/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

It creates:

- a **Live matches** sensor whose state is the number of matches in play, and
- one **sensor per live match** whose state is a compact score
  (e.g. `4-6 6-2 4-2 | 30-15`) with players, tournament, round, surface,
  server, sets, games and points as attributes.

Matches appear as they go live and become `unavailable` when they finish and
drop out of the live feed.

## Requirements

- Home Assistant 2024.8 or newer.
- A Live Tennis API key. The **free tier** (30 requests/min, 100 requests/day,
  no card required) is enough at the default settings — get one at
  <https://livetennisapi.com/subscribe/free>. If you select more than one tour,
  raise the update interval (or upgrade to Basic) as described in
  [A note on your quota](#a-note-on-your-quota).

## Installation (HACS custom repository)

1. In Home Assistant, open **HACS → Integrations**.
2. Open the overflow menu (⋮) → **Custom repositories**.
3. Add `https://github.com/livetennisapi/ha-livetennis` with category
   **Integration**, then click **Add**.
4. Find **Live Tennis** in the list, click **Download**, and restart Home
   Assistant.

> HACS requires the repository to have a description, topics, and at least one
> published GitHub release/tag. Maintainers: tag a release (e.g. `v1.0.0`)
> before submitting.

## Manual installation

Copy `custom_components/livetennis/` into your Home Assistant
`config/custom_components/` directory and restart.

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **Live Tennis**.
3. Enter your API key and choose:
   - **Tours to track** — leave empty for all tours, or pick a subset. Each
     selected tour is one API request per update cycle.
   - **Update interval** — default 900 s (minimum 60 s, maximum 3600 s). The
     default is fine for the per-minute limit with any tour selection, but on
     the free tier the **daily** limit is the one that matters once you select
     multiple tours or lower the interval — see
     [A note on your quota](#a-note-on-your-quota).
   - **Create a sensor per live match** — on by default.

An invalid key is reported immediately (the key is validated with a live call —
keys look like `twjp_...`). The integration authenticates with the `X-API-Key`
header; the API also accepts `Authorization: Bearer <key>` for your own
scripts and REST sensors.

You can change tours, the interval, and the per-match toggle later via the
integration's **Configure** button. If your key is later revoked or replaced,
Home Assistant prompts you to **re-authenticate** with a new key — no need to
delete and re-add the integration.

### API usage and tiers

The integration only calls `GET /matches?status=live`, which is available on
**every** tier including FREE. Current quota grid:

| Tier | Requests/min | Requests/day | Price |
| --- | --- | --- | --- |
| FREE | 30 | 100 | $0 |
| BASIC | 60 | 1,000 | $9.99/mo |
| PRO | 300 | 10,000 | $29.99/mo |
| ULTRA | 600 | 500,000 | $99.99/mo |

On a free key, keep the update interval at 900 s or slower; for an always-on
dashboard (faster updates or several tours), **Basic is recommended**.

### A note on your quota

A free key allows 30 requests/minute and **100 requests/day**. Each update
cycle costs **one request per selected tour** — or a single request when no
tours are selected (one unfiltered call covers everything). At the default
900 s interval that is `86400 / 900 = 96` cycles/day, so the daily cost scales
with the number of tours you pick:

| Tours selected | Requests/cycle | Requests/day @ 900 s | Free tier (100/day) | Recommended interval |
| --- | --- | --- | --- | --- |
| none (all tours) | 1 | 96 | ✅ fits | 900 s (default) |
| 1 | 1 | 96 | ✅ fits | 900 s (default) |
| 2 | 2 | 192 | ❌ over | 1800 s → 96/day |
| 3 | 3 | 288 | ❌ over | 2700 s → 96/day |
| 4 | 4 | 384 | ❌ over | 3600 s → 96/day |
| 5 | 5 | 480 | ❌ over | doesn't fit free — even the 3600 s maximum is 120/day. Use Basic. |

The 900 s default fits the free tier for the most common setups (no tour
filter, or a single tour) with almost no headroom — 96 of 100 requests/day —
so don't lower the interval on a free key: even at 900 s a second tour puts
you over, and at the 60 s minimum a single tour costs 1,440 requests/day. If
you want faster updates (or several tours at a reasonable interval), the
**Basic** tier ($9.99, 1,000 requests/day) sustains one tour at ~90 s, or all
five tours at 450 s (960/day). The per-minute limit is never the constraint:
even 5 requests per cycle at the 60 s minimum is 5 requests/minute, far
below 30.

### What happens when you hit a limit

- An ordinary **429** (minute or day window) is treated as a transient failure;
  polling simply continues on the next cycle.
- A **429 `abuse_throttled`** response means the API has temporarily blocked the
  key for chronically exceeding its quota (typically for 24 hours — usually a
  broken retry loop in *some* client using the same key). The integration stops
  polling until the block lifts (`retry_at_epoch`), logs a warning, and raises a
  **repair issue** in Settings → Repairs. Polling and the repair reset
  automatically once the API serves data again.

## Entities

| Entity | State | Notes |
| --- | --- | --- |
| `sensor.live_matches` | count of live matches | attributes: `match_ids`, `tournaments` |
| `sensor.tennis_<p1>_vs_<p2>` | compact score | one per live match when enabled |

Per-match sensor attributes include: `player_1`/`player_2`, `tournament`,
`round`, `surface`, `indoor`, `format`, `server`/`server_name`, `set_score`,
`sets_won`, `games_player_1`/`games_player_2`, `points`, `current_points`,
`is_tiebreak`, `score_updated`, `scheduled_time`, and rankings/countries when
available.

### Notes on live data

- `server` is `null` for a small fraction of live matches; `server`/
  `server_name` are then `null`.
- Upcoming matches have no score; their state is the lifecycle status
  (e.g. `upcoming`).
- Points are strings (`"40"`, `"AD"`) and are exposed as-is.

## Brand icon / logo

Home Assistant brand images (the icon and logo shown in the UI) are **not**
shipped in this repository — they are submitted separately to
[home-assistant/brands](https://github.com/home-assistant/brands) under the
`livetennis` domain. Until that PR is merged the integration works but shows a
default icon.

## Development

`custom_components/livetennis/api.py` and `helpers.py` have no Home Assistant
imports, so the API client and the score/attribute formatting can be tested
standalone against live JSON.

## Disclaimer

Not affiliated with the ATP, WTA, ITF, or any tournament. Data is provided by
the Live Tennis API under its own terms.

## Affiliate program

Know developers who need tennis data? The [affiliate program](https://affiliates.livetennisapi.com/program) pays 51% recurring commission for the life of every referred subscription — 30-day cookie, and the people you refer get 10% off.

## Links

- API documentation: <https://docs.livetennisapi.com>
- Free API key: <https://livetennisapi.com/subscribe/free>
- Discord: <https://discord.gg/f8WUZHgDm6>
- GitHub org: <https://github.com/livetennisapi>

## License

[MIT](LICENSE)
