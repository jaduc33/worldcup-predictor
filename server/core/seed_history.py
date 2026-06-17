"""Backfill match_history.json with finished matches involving World Cup 2026 teams.

Two entry points:
- seed_recent_friendlies(): scans the ~3-day API-Football date window around
  today for any finished match involving a WC team (designed for pre-tournament
  friendlies). Uses eloratings.net for pre-match ratings.
- seed_world_cup_results(): scans from the tournament start (2026-06-11) to
  today for finished World Cup matches (league_id=1). Updates Elo ratings
  sequentially by kick-off time, just like update_match_result, so the Elo
  file reflects every match already played.

Both are idempotent: each fixture's API-Football id is stored in
match_history.json and used to skip duplicates on rerun.

Free-plan date window: `fixtures?date=` covers a rolling ~3-day window.
seed_world_cup_results tries all dates since the tournament start; dates older
than the API window return an empty response (or an error, which is caught
per-date) and are simply skipped.
"""

from datetime import date, timedelta

from server.core import data, elo, fetch
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


_WC_START = date(2026, 6, 11)


def _default_dates() -> list[str]:
    today = date.today()
    return [(today + timedelta(days=offset)).isoformat() for offset in (-1, 0, 1)]


def _dates_since_wc_start() -> list[str]:
    today = date.today()
    start = min(_WC_START, today)
    return [(start + timedelta(days=i)).isoformat() for i in range((today - start).days + 1)]


def _fetch_stats(fx: dict) -> dict | None:
    """Fetch parsed fixture statistics from football_api; returns None on any error."""
    try:
        return api.fixture_statistics(fx["fixture"]["id"])
    except api.APIFootballError:
        return None


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
            stats = _fetch_stats(fx)
            if stats:
                entry["stats"] = stats
            data.append_match_history(entry)
            seen_ids.add(entry["fixture_id"])
            added.append(entry)

    return {"added": len(added), "matches": added}


def seed_world_cup_results(dates: list[str] | None = None) -> dict:
    """Fetch finished World Cup (league_id=1) matches on `dates`, update Elo
    ratings sequentially by kick-off time, and append results to
    match_history.json.

    Defaults to every date from the tournament start (2026-06-11) to today.
    Dates outside the free-plan API window are silently skipped (empty response
    or APIFootballError). Matches are processed in chronological kick-off order
    so each team's Elo reflects the correct pre-match rating.
    """
    wc_teams = set(data.all_teams())
    seen_ids = {e["fixture_id"] for e in data.load_match_history() if "fixture_id" in e}

    scan_dates = dates if dates is not None else _dates_since_wc_start()

    # Collect all new finished WC matches, tolerating per-date API errors
    candidates = []
    date_errors = []
    for d in scan_dates:
        try:
            for fx in api.fixtures_on_date(d):
                if fx["league"]["id"] != api.WORLD_CUP_LEAGUE_ID:
                    continue
                s = api.simplify_fixture(fx)
                if s["status"] != "Match Finished":
                    continue
                fixture_id = fx["fixture"]["id"]
                if fixture_id in seen_ids:
                    continue
                home = _NAME_MAP.get(s["home"], s["home"])
                away = _NAME_MAP.get(s["away"], s["away"])
                if home not in wc_teams or away not in wc_teams:
                    continue
                if s["score"] is None:
                    continue
                candidates.append((fx["fixture"]["date"], fx, home, away, s, fixture_id))
        except api.APIFootballError as exc:
            date_errors.append({"date": d, "error": str(exc)})

    # Process in kick-off order so Elo updates are sequential
    candidates.sort(key=lambda x: x[0])

    added = []
    for _, fx, home, away, s, fixture_id in candidates:
        try:
            r_home = data.rating_of(home)
            r_away = data.rating_of(away)
        except KeyError:
            continue

        score_home, score_away = (int(x) for x in s["score"].split("-"))
        outcome = (
            "home_win" if score_home > score_away
            else "draw" if score_home == score_away
            else "away_win"
        )

        new_home, new_away = elo.update_ratings(r_home, r_away, score_home, score_away)
        ratings = dict(data.load_ratings())
        ratings[home] = new_home
        ratings[away] = new_away
        data.save_ratings(ratings, source="post-match")

        entry = {
            "home": home, "away": away,
            "score_home": score_home, "score_away": score_away,
            "rating_home_pre": r_home, "rating_away_pre": r_away,
            "outcome": outcome,
            "competition": fx["league"]["name"],
            "fixture_id": fixture_id,
        }
        stats = _fetch_stats(fx)
        if stats:
            entry["stats"] = stats
        data.append_match_history(entry)
        seen_ids.add(fixture_id)
        added.append({
            "match": f"{home} {score_home}-{score_away} {away}",
            "date": fx["fixture"]["date"][:10],
            "elo_changes": {
                home: round(new_home - r_home, 1),
                away: round(new_away - r_away, 1),
            },
        })

    result: dict = {"added": len(added), "matches": added}
    if date_errors:
        result["date_errors"] = date_errors
    return result


def backfill_match_stats() -> dict:
    """Fetch and attach statistics (shots, possession, passes, xG) for all
    match_history.json entries that have a fixture_id but no stats yet.

    Safe to call repeatedly — entries that already have stats are skipped.
    Uses the cached fixture_statistics endpoint (7-day TTL) so repeated calls
    cost no extra API quota.
    """
    import json

    history = list(data.load_match_history())
    updated = 0
    errors = []

    for i, entry in enumerate(history):
        if "fixture_id" not in entry or "stats" in entry:
            continue
        try:
            stats = api.fixture_statistics(entry["fixture_id"])
            if stats:
                history[i] = {**entry, "stats": stats}
                updated += 1
        except api.APIFootballError as exc:
            errors.append({"fixture_id": entry["fixture_id"], "error": str(exc)})

    if updated:
        data.HISTORY_FILE.write_text(
            json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        data.load_match_history.cache_clear()

    result: dict = {"updated": updated}
    if errors:
        result["errors"] = errors
    return result
