"""Pure-formatting unit tests (no network, no API key) for helpers.py.

These exercise the live-data shapes and gotchas confirmed against the real API.
"""

from custom_components.livetennis import helpers


def _match(score):
    return {
        "id": 1,
        "status": "live",
        "tournament": "Test Cup",
        "players": {"p1": {"name": "Alpha"}, "p2": {"name": "Beta"}},
        "score": score,
    }


def test_state_live_with_points():
    m = _match(
        {
            "games": [[6, 3], [4, 5]],
            "sets": [1, 0],
            "points": ["40", "30"],
            "server": 1,
            "is_tiebreak": False,
        }
    )
    assert helpers.format_state(m) == "6-4 3-5 | 40-30"


def test_null_server_is_handled():
    m = _match(
        {
            "games": [[6], [4]],
            "sets": [0, 0],
            "points": ["15", "0"],
            "server": None,
            "is_tiebreak": False,
        }
    )
    attrs = helpers.match_attributes(m)
    assert attrs["server"] is None
    assert attrs["server_name"] is None


def test_tiebreak_state():
    m = _match(
        {
            "games": [[6], [6]],
            "sets": [0, 0],
            "points": ["5", "3"],
            "server": 2,
            "is_tiebreak": True,
        }
    )
    assert helpers.format_state(m) == "6-6 | TB 5-3"


def test_upcoming_null_score():
    assert helpers.format_state({"status": "upcoming", "score": None}) == "upcoming"


def test_string_points_ad():
    m = _match(
        {
            "games": [[3], [3]],
            "sets": [0, 0],
            "points": ["AD", "40"],
            "server": 1,
            "is_tiebreak": False,
        }
    )
    assert helpers.format_state(m) == "3-3 | AD-40"


def test_empty_games_render_zero():
    m = _match(
        {
            "games": [[], []],
            "sets": [0, 0],
            "points": ["0", "0"],
            "server": 1,
            "is_tiebreak": False,
        }
    )
    assert helpers.format_state(m) == "0-0 | 0-0"


def test_doubles_team_names_and_server():
    m = {
        "id": 2,
        "status": "live",
        "is_doubles": True,
        "players": {
            "p1": {"name": "Aa/Bb", "is_doubles_team": True,
                   "data_completeness": {"known": None, "of": None, "note": "doubles team"}},
            "p2": {"name": "Cc/Dd", "is_doubles_team": True,
                   "data_completeness": {"known": None, "of": None, "note": "doubles team"}},
        },
        "score": {"games": [[6], [4]], "sets": [0, 0], "points": ["0", "0"],
                  "server": 2, "is_tiebreak": False},
    }
    assert helpers.match_title(m) == "Aa/Bb vs Cc/Dd"
    assert helpers.match_attributes(m)["server_name"] == "Cc/Dd"
