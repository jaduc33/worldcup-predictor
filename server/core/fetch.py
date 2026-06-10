"""Fetch live national-team Elo ratings from eloratings.net.

The site is a JS single-page app; the actual numbers live in two
tab-separated data files served as plain text:

  - en.teams.tsv  -> "{code}\\t{english name}\\t{aliases...}"   (code -> name)
  - World.tsv     -> "{rank}\\t{rank}\\t{code}\\t{current elo}\\t{...}" (code -> rating)

We fetch both, join on the 2-letter code, and map a handful of names that
differ from our internal naming (groups.json).
"""

import httpx

from server.core import data

_BASE = "https://eloratings.net"
_TEAMS_URL = f"{_BASE}/en.teams.tsv"
_WORLD_URL = f"{_BASE}/World.tsv"

# eloratings.net name -> our internal name (groups.json)
_NAME_MAP: dict[str, str] = {
    "Turkey": "Turkiye",
    "United States": "USA",
    "Curaçao": "Curacao",
}

_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) worldcup-predictor/1.0"}


def fetch_live_ratings(timeout: float = 15.0) -> dict[str, float]:
    """Return {team_name: elo_rating} for all national teams ranked by eloratings.net."""
    code_to_name = _fetch_team_names(timeout)
    return _fetch_world_ratings(code_to_name, timeout)


def _fetch_team_names(timeout: float) -> dict[str, str]:
    resp = httpx.get(_TEAMS_URL, timeout=timeout, follow_redirects=True, headers=_HEADERS)
    resp.raise_for_status()

    code_to_name: dict[str, str] = {}
    for line in resp.text.splitlines():
        fields = line.split("\t")
        if len(fields) < 2:
            continue
        code, name = fields[0], fields[1]
        code_to_name[code] = _NAME_MAP.get(name, name)
    return code_to_name


def _fetch_world_ratings(code_to_name: dict[str, str], timeout: float) -> dict[str, float]:
    resp = httpx.get(_WORLD_URL, timeout=timeout, follow_redirects=True, headers=_HEADERS)
    resp.raise_for_status()

    ratings: dict[str, float] = {}
    for line in resp.text.splitlines():
        fields = line.split("\t")
        if len(fields) < 4:
            continue
        code, rating_str = fields[2], fields[3]
        name = code_to_name.get(code)
        if name is None:
            continue
        try:
            ratings[name] = float(rating_str)
        except ValueError:
            continue

    if len(ratings) < 20:
        raise ValueError(
            f"Only parsed {len(ratings)} ratings from {_WORLD_URL} — "
            "the data format may have changed."
        )
    return ratings


def apply_live_ratings(timeout: float = 15.0) -> dict:
    """Fetch ratings, merge with existing file, persist, and return a summary.

    Only teams already in elo_ratings.json are updated — we don't add new teams
    automatically, to avoid name-mismatch surprises.
    """
    fetched = fetch_live_ratings(timeout=timeout)
    current = dict(data.load_ratings())  # copy so we can mutate safely

    updated, skipped = [], []
    for team in list(current.keys()):
        if team in fetched:
            current[team] = fetched[team]
            updated.append(team)
        else:
            skipped.append(team)

    data.save_ratings(current, source="eloratings.net")

    return {
        "updated": len(updated),
        "skipped": len(skipped),
        "skipped_teams": skipped,
        "source": _WORLD_URL,
    }
