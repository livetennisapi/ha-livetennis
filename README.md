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

- Home Assistant 2024.1 or newer.
- A Live Tennis API key. The **free tier** (1000 requests/day, 30 requests/min)
  covers everything this integration uses — get one at
  <https://livetennisapi.com/subscribe/free>.

## Installation (HACS custom repository)

1. In Home Assistant, open **HACS → Integrations**.
2. Open the overflow menu (⋮) → **Custom repositories**.
3. Add `https://github.com/bensynapse/ha-livetennis` with category
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
   - **Update interval** — default 120 s (minimum 60 s). The free tier allows
     30 requests/minute; the default stays well within that even with every
     tour selected.
   - **Create a sensor per live match** — on by default.

An invalid key is reported immediately (the key is validated with a live call).

You can change tours, the interval, and the per-match toggle later via the
integration's **Configure** button.

## Entities

| Entity | State | Notes |
| --- | --- | --- |
| `sensor.live_tennis_live_matches` | count of live matches | attributes: `match_ids`, `tournaments` |
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

## License

[MIT](LICENSE)
