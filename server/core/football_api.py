"""Client for API-Football (api-sports.io) — schedule, live scores, H2H, injuries.

Requires the API_FOOTBALL_KEY env var (api-sports.io direct key, sent as the
x-apisports-key header). Every call goes through server.core.cache so repeated
lookups during the tournament stay within the free-tier daily quota (100/day).

Free-plan constraints that shape this module:
  - league=1 (World Cup) + season=2026 is BLOCKED ("try from 2022 to 2024").
  - The `last` and `next` fixture parameters are BLOCKED.
  - `fixtures?date=` only accepts a ~3-day rolling window around today.
  - `fixtures?live=all` and `fixtures?date=` work WITHOUT league/season, so we
    fetch globally and filter to World Cup matches client-side (league id 1).
"""

import os

import httpx

from server.core import cache

_BASE = "https://v3.football.api-sports.io"
WORLD_CUP_LEAGUE_ID = 1

# TTLs (seconds)
_TTL_SCHEDULE = 5 * 60
_TTL_LIVE = 60
_TTL_H2H = 7 * 24 * 3600
_TTL_INJURIES = 5 * 60
_TTL_TEAM_ID = 30 * 24 * 3600  # team IDs are static


class APIFootballError(Exception):
    pass


def simplify_fixture(fx: dict) -> dict:
    """Reduce a raw API-Football fixture object to the fields callers need."""
    fixture, teams, goals = fx["fixture"], fx["teams"], fx["goals"]
    return {
        "date": fixture["date"],
        "status": fixture["status"]["long"],
        "venue": (fixture.get("venue") or {}).get("name"),
        "home": teams["home"]["name"],
        "away": teams["away"]["name"],
        "score": f"{goals['home']}-{goals['away']}" if goals["home"] is not None else None,
    }


def _headers() -> dict:
    key = os.environ.get("API_FOOTBALL_KEY")
    if not key:
        raise APIFootballError("API_FOOTBALL_KEY is not set. Add it to your .env file.")
    return {"x-apisports-key": key}


def _get(endpoint: str, params: dict) -> dict:
    resp = httpx.get(f"{_BASE}/{endpoint}", params=params, headers=_headers(), timeout=15.0)
    resp.raise_for_status()
    body = resp.json()
    if body.get("errors"):
        raise APIFootballError(str(body["errors"]))
    return body


def team_id(name: str) -> int:
    """Resolve a team name to its API-Football team ID (cached indefinitely)."""
    def fetch():
        body = _get("teams", {"name": name})
        results = body.get("response", [])
        if not results:
            raise APIFootballError(f"No API-Football team found for '{name}'")
        return results[0]["team"]["id"]
    return cache.cached(f"team_id_{name}", _TTL_TEAM_ID, fetch)


def fixtures_on_date(date: str) -> list[dict]:
    """All global fixtures on `date` (YYYY-MM-DD). Free plan only allows ~today +/- 1 day."""
    def fetch():
        body = _get("fixtures", {"date": date})
        return body.get("response", [])
    return cache.cached(f"fixtures_{date}", _TTL_SCHEDULE, fetch)


def live_fixtures() -> list[dict]:
    """Currently in-play fixtures, globally (filter to World Cup client-side)."""
    def fetch():
        body = _get("fixtures", {"live": "all"})
        return body.get("response", [])
    return cache.cached("live_fixtures", _TTL_LIVE, fetch)


def head_to_head(team_a: str, team_b: str) -> list[dict]:
    """All available past meetings between two national teams (any competition).

    The `last` parameter is not available on the free plan, so we fetch
    everything and let the caller sort/slice.
    """
    id_a, id_b = team_id(team_a), team_id(team_b)
    key = f"h2h_{min(id_a, id_b)}_{max(id_a, id_b)}"

    def fetch():
        body = _get("fixtures/headtohead", {"h2h": f"{id_a}-{id_b}"})
        return body.get("response", [])
    return cache.cached(key, _TTL_H2H, fetch)


_TTL_STATS = 7 * 24 * 3600  # stats are immutable once a match is finished


def fixture_statistics(fixture_id: int) -> list[dict]:
    """Per-team statistics for a finished fixture (possession, shots, passes…)."""
    def fetch():
        body = _get("fixtures/statistics", {"fixture": fixture_id})
        return body.get("response", [])
    return cache.cached(f"stats_{fixture_id}", _TTL_STATS, fetch)


def injuries(team: str, date: str) -> list[dict]:
    """Injury list for a national team on `date` (YYYY-MM-DD).

    Uses team+date instead of team+season to avoid the season=2026 block.
    """
    tid = team_id(team)

    def fetch():
        body = _get("injuries", {"team": tid, "date": date})
        return body.get("response", [])
    return cache.cached(f"injuries_{tid}_{date}", _TTL_INJURIES, fetch)
