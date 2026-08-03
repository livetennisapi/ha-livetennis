# Live Tennis for Home Assistant

A [HACS](https://hacs.xyz)-installable custom integration that surfaces **live
tennis scores** (ATP / WTA / Challenger / ITF / Juniors) in Home Assistant,
powered by the [Live Tennis API](https://livetennisapi.com).

It creates:

- a **Live matches** sensor whose state is the number of matches in play, and
- one **sensor per live match** whose state is a compact score
  (e.g. `4-6 6-2 4-2 | 30-15`) with players, tournament, round, surface,
  server, sets, games and points as attributes.

Matches appear as they go live and become `unavailable` when they finish and
drop out of the live feed.

## Requirements

- Home Assistant 2024.8 or newer.
- A Live Tennis API key. The **free tier** (30 requests/min, 1,000 requests/day,
  no card required) is enough at the default settings — get one at
  <https://livetennisapi.com/subscribe/free>. If you select more than one tour,
  raise the update interval as described in
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
   - **Update interval** — default 120 s (minimum 60 s, maximum 3600 s). The
     default is fine for the per-minute limit with any tour selection, but on
     the free tier the **daily** limit is the one that matters once you select
     multiple tours — see [A note on your quota](#a-note-on-your-quota).
   - **Create a sensor per live match** — on by default.

An invalid key is reported immediately (the key is validated with a live call).

You can change tours, the interval, and the per-match toggle later via the
integration's **Configure** button.

### A note on your quota

A free key allows 30 requests/minute and **1,000 requests/day**. Each update
cycle costs **one request per selected tour** — or a single request when no
tours are selected (one unfiltered call covers everything). At the default
120 s interval that is `86400 / 120 = 720` cycles/day, so the daily cost scales
with the number of tours you pick:

| Tours selected | Requests/cycle | Requests/day @ 120 s | Free tier (1,000/day) | Recommended interval |
| --- | --- | --- | --- | --- |
| none (all tours) | 1 | 720 | ✅ fits | 120 s (default) |
| 1 | 1 | 720 | ✅ fits | 120 s (default) |
| 2 | 2 | 1,440 | ❌ over | 180 s → 960/day |
| 3 | 3 | 2,160 | ❌ over | 300 s → 864/day |
| 4 | 4 | 2,880 | ❌ over | 360 s → 960/day |
| 5 | 5 | 3,600 | ❌ over | 450 s → 960/day |

The default stays at 120 s because it is correct for the most common setups
(no tour filter, or a single tour). The per-minute limit is never the
constraint: even 5 requests per cycle at the 60 s minimum interval is
5 requests/minute, far below 30 — but note that at 60 s even a single tour
costs 1,440 requests/day, so don't lower the interval on a free key.

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

## License

[MIT](LICENSE)
