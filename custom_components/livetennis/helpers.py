"""Pure formatting helpers for Live Tennis matches.

No Home Assistant imports and no relative imports: this module maps raw API
match dicts to a compact state string and a flat attribute dict, and is designed
to be unit-tested standalone against live JSON.

The API shapes we defend against (all confirmed against live data):
  * ``score`` is ``null`` for upcoming matches.
  * ``score.server`` is ``null`` in a minority of live matches (~7%).
  * ``score.points`` are strings ("40", "AD").
  * ``score.games`` is ``[[p1 per set], [p2 per set]]`` and grows as sets start.
  * ``score.sets`` is ``[sets_won_p1, sets_won_p2]``.
  * doubles teams carry ``data_completeness`` = null-ish with a ``note``.
"""

from __future__ import annotations

from typing import Any

STATE_MAX_LEN = 255  # Home Assistant hard limit on state length.


def _player_name(match: dict[str, Any], key: str) -> str | None:
    player = (match.get("players") or {}).get(key) or {}
    name = player.get("name")
    return name if isinstance(name, str) else None


def set_scores(score: dict[str, Any] | None) -> list[str]:
    """Return per-set score strings like ``["4-6", "6-2", "4-2"]``.

    ``games`` may be shorter/uneven while a set is starting; we zip defensively.
    """
    if not score:
        return []
    games = score.get("games") or []
    if len(games) < 2 or not isinstance(games[0], list) or not isinstance(games[1], list):
        return []
    p1_games, p2_games = games[0], games[1]
    pairs = zip(p1_games, p2_games)
    return [f"{a}-{b}" for a, b in pairs]


def points_pair(score: dict[str, Any] | None) -> str | None:
    """Return ``"30-15"`` (points are strings) or None when unavailable."""
    if not score:
        return None
    points = score.get("points")
    if isinstance(points, list) and len(points) >= 2:
        p1, p2 = points[0], points[1]
        if p1 is not None and p2 is not None:
            return f"{p1}-{p2}"
    return None


def format_state(match: dict[str, Any]) -> str:
    """Return a compact human-readable state for a match.

    Live example: ``"4-6 6-2 4-2 | 30-15"``. Upcoming (null score) returns the
    lifecycle status (e.g. ``"upcoming"``).
    """
    score = match.get("score")
    if not score:
        return str(match.get("status") or "unknown")

    sets = set_scores(score)
    body = " ".join(sets) if sets else "0-0"

    if score.get("is_tiebreak"):
        pts = points_pair(score)
        state = f"{body} | TB {pts}" if pts else f"{body} | tiebreak"
    else:
        pts = points_pair(score)
        state = f"{body} | {pts}" if pts else body

    return state[:STATE_MAX_LEN]


def _server_info(match: dict[str, Any], score: dict[str, Any]) -> tuple[int | None, str | None]:
    """Return (server_side, server_name). server is null in some live matches."""
    server = score.get("server")
    if server == 1:
        return 1, _player_name(match, "p1")
    if server == 2:
        return 2, _player_name(match, "p2")
    return None, None


def match_attributes(match: dict[str, Any]) -> dict[str, Any]:
    """Return a flat, JSON-safe attribute dict for a match sensor."""
    score = match.get("score") or {}
    server_side, server_name = _server_info(match, score) if score else (None, None)

    attrs: dict[str, Any] = {
        "match_id": match.get("id"),
        "status": match.get("status"),
        "tournament": match.get("tournament"),
        "round": match.get("round"),
        "surface": match.get("surface"),
        "indoor": match.get("indoor"),
        "format": match.get("format"),
        "is_doubles": match.get("is_doubles"),
        "scheduled_time": match.get("scheduled_time"),
        "player_1": _player_name(match, "p1"),
        "player_2": _player_name(match, "p2"),
        "player_1_country": ((match.get("players") or {}).get("p1") or {}).get("country"),
        "player_2_country": ((match.get("players") or {}).get("p2") or {}).get("country"),
        "player_1_ranking": ((match.get("players") or {}).get("p1") or {}).get("ranking"),
        "player_2_ranking": ((match.get("players") or {}).get("p2") or {}).get("ranking"),
    }

    if score:
        attrs.update(
            {
                "set_score": set_scores(score),
                "sets_won": score.get("sets"),
                "games_player_1": (score.get("games") or [None, None])[0],
                "games_player_2": (score.get("games") or [None, None])[1],
                "points": score.get("points"),
                "current_points": points_pair(score),
                "server": server_side,
                "server_name": server_name,
                "is_tiebreak": bool(score.get("is_tiebreak")),
                "score_updated": score.get("timestamp"),
            }
        )

    # Completed matches expose a derived winner; harmless to surface if present.
    if match.get("winner") is not None:
        attrs["winner"] = match.get("winner")

    return attrs


def match_title(match: dict[str, Any]) -> str:
    """Human name for a per-match entity, e.g. ``"Skrobarcek vs Gorin"``."""
    p1 = _player_name(match, "p1") or "TBD"
    p2 = _player_name(match, "p2") or "TBD"
    return f"{p1} vs {p2}"
