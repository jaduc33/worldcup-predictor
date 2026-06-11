"""Backfill match_history.json with recently-finished friendlies involving
World Cup 2026 teams.

The free API-Football plan has no season-agnostic "team's last N matches"
endpoint (season is locked to 2022-2024 and `last`/`next` are blocked -- see
football_api.py), so the only reachable source of recent results is
`fixtures_on_date`, which itself only covers a ~3-day window around today.
This scans that window for finished matches involving a World Cup team, tags
each with its competition (for form.py's competition-weighted average), and
records it via data.append_match_history -- using eloratings.net
(fetch.fetch_live_ratings, no API-Football cost) for pre-match ratings of both
sides, since data/elo_ratings.json is itself sourced from eloratings.net.

Safe to call repeatedly: each fixture's API-Football id is stored as
"fixture_id" and used to skip duplicates on rerun.
"""

from datetime import date, timedelta

from server.core import data, fetch
from server.core import football_api as api

# API-Football team name -> our internal name (groups.json / eloratings.net),
# for the handful of teams whose naming differs between the two sources.
_NAME_MAP: dict[str, str] = {
    "Czech Republic": "Czechia",
    "United States": "USA",
    "Korea Republic": "South Korea",
    "IR Iran": "Iran",
    "Côte d'Ivoire": "Ivory Coast",
    "Cape Verde Islands": "Cape Verde",
}


def _default_dates() -> list[str]:
    today = date.today()
    return [(today + timedelta(days=offset)).isoformat() for offset in (-1, 0, 1)]


def _entry_from_fixture(fx: dict, wc_teams: set[str], live_ratings: dict[str, float],
                         seen_ids: set[int]) -> dict | None:
    s = api.simplify_fixture(fx)
    if s["status"] != "Match Finished":
        return None

    fixture_id = fx["fixture"]["id"]
    if fixture_id in seen_ids:
        return None

    home = _NAME_MAP.get(s["home"], s["home"])
    away = _NAME_MAP.get(s["away"], s["away"])
    if home not in wc_teams and away not in wc_teams:
        return None
    if home not in live_ratings or away not in live_ratings:
        return None

    score_home, score_away = (int(x) for x in s["score"].split("-"))
    outcome = (
        "home_win" if score_home > score_away
        else "draw" if score_home == score_away
        else "away_win"
    )
    return {
        "home": home, "away": away,
        "score_home": score_home, "score_away": score_away,
        "rating_home_pre": live_ratings[home], "rating_away_pre": live_ratings[away],
        "outcome": outcome,
        "competition": fx["league"]["name"],
        "fixture_id": fixture_id,
    }


def seed_recent_friendlies(dates: list[str] | None = None) -> dict:
    """Scan `dates` (default: yesterday/today/tomorrow) for finished fixtures
    involving a World Cup team and append any not already recorded to
    match_history.json. Returns a summary of what was added.
    """
    wc_teams = set(data.all_teams())
    live_ratings = fetch.fetch_live_ratings()
    seen_ids = {e["fixture_id"] for e in data.load_match_history() if "fixture_id" in e}

    added = []
    for d in dates if dates is not None else _default_dates():
        for fx in api.fixtures_on_date(d):
            entry = _entry_from_fixture(fx, wc_teams, live_ratings, seen_ids)
            if entry is None:
                continue
            data.append_match_history(entry)
            seen_ids.add(entry["fixture_id"])
            added.append(entry)

    return {"added": len(added), "matches": added}
