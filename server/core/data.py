"""Data access: load groups and ratings, plus small lookup helpers."""

import json
from functools import lru_cache
from itertools import combinations
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
RATINGS_FILE = DATA_DIR / "elo_ratings.json"
HISTORY_FILE = DATA_DIR / "match_history.json"


@lru_cache
def load_groups() -> dict:
    return json.loads((DATA_DIR / "groups.json").read_text(encoding="utf-8"))["groups"]


@lru_cache
def load_hosts() -> list[str]:
    return json.loads((DATA_DIR / "groups.json").read_text(encoding="utf-8"))["hosts"]


@lru_cache
def load_ratings() -> dict:
    return json.loads(RATINGS_FILE.read_text(encoding="utf-8"))["ratings"]


def save_ratings(ratings: dict[str, float], source: str = "live") -> None:
    """Persist updated ratings to disk and invalidate the in-memory cache."""
    blob = json.loads(RATINGS_FILE.read_text(encoding="utf-8"))
    blob["ratings"] = {k: round(v, 1) for k, v in ratings.items()}
    blob["source"] = source
    RATINGS_FILE.write_text(json.dumps(blob, indent=2, ensure_ascii=False), encoding="utf-8")
    load_ratings.cache_clear()


def reload_ratings() -> dict:
    """Force a cache-busting reload of ratings from disk."""
    load_ratings.cache_clear()
    return load_ratings()


@lru_cache
def load_match_history() -> list[dict]:
    return json.loads(HISTORY_FILE.read_text(encoding="utf-8")) if HISTORY_FILE.exists() else []


def append_match_history(entry: dict) -> None:
    """Append a played match's pre-match ratings/score to match_history.json."""
    history = list(load_match_history())
    history.append(entry)
    HISTORY_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
    load_match_history.cache_clear()


def all_teams() -> list[str]:
    return sorted({t for teams in load_groups().values() for t in teams})


def group_of(team: str) -> str | None:
    for g, teams in load_groups().items():
        if team in teams:
            return g
    return None


def rating_of(team: str) -> float:
    ratings = load_ratings()
    if team not in ratings:
        raise KeyError(f"No rating for '{team}'. Try one of: {all_teams()}")
    return ratings[team]


def group_fixtures(group: str) -> list[dict]:
    """The 6 round-robin pairings of a group (dates to be enriched later)."""
    teams = load_groups()[group]
    return [{"home": a, "away": b, "date": None} for a, b in combinations(teams, 2)]
