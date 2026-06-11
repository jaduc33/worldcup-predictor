"""MCP tools: live data refresh, post-match Elo updates, tournament status."""

import json
from pathlib import Path

from server.core import data, elo, fetch, seed_history

_PREDICTIONS_FILE = Path(__file__).resolve().parents[2] / "data" / "predictions.json"
_OUTCOMES = ("home_win", "draw", "away_win")


def _load_predictions() -> list:
    return json.loads(_PREDICTIONS_FILE.read_text(encoding="utf-8")) if _PREDICTIONS_FILE.exists() else []


def _save_predictions(records: list) -> None:
    _PREDICTIONS_FILE.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")


def register(mcp):

    @mcp.tool
    def refresh_ratings() -> dict:
        """Fetch the latest national-team Elo ratings from eloratings.net and update the data file."""
        try:
            return fetch.apply_live_ratings()
        except Exception as exc:
            return {"error": str(exc)}

    @mcp.tool
    def update_match_result(home: str, away: str, score_home: int, score_away: int) -> dict:
        """Record the real score of a match, update both teams' Elo ratings, and settle any open prediction.

        outcome is derived from the score: home_win | draw | away_win.
        """
        try:
            r_home = data.rating_of(home)
            r_away = data.rating_of(away)
        except KeyError as exc:
            return {"error": str(exc)}

        new_home, new_away = elo.update_ratings(r_home, r_away, score_home, score_away)

        ratings = dict(data.load_ratings())
        ratings[home] = new_home
        ratings[away] = new_away
        data.save_ratings(ratings, source="post-match")

        outcome = (
            "home_win" if score_home > score_away
            else "draw" if score_home == score_away
            else "away_win"
        )

        data.append_match_history({
            "home": home, "away": away,
            "score_home": score_home, "score_away": score_away,
            "rating_home_pre": r_home, "rating_away_pre": r_away,
            "outcome": outcome,
            "competition": "World Cup",
        })

        # Settle the most recent open prediction for this match, if any
        records = _load_predictions()
        settled = False
        for rec in reversed(records):
            if rec["home"] == home and rec["away"] == away and rec["result"] is None:
                rec["result"] = outcome
                rec["actual_score"] = f"{score_home}-{score_away}"
                settled = True
                break
        if settled:
            _save_predictions(records)

        return {
            "match": f"{home} {score_home}-{score_away} {away}",
            "outcome": outcome,
            "elo_changes": {
                home: {"before": r_home, "after": new_home, "delta": round(new_home - r_home, 1)},
                away: {"before": r_away, "after": new_away, "delta": round(new_away - r_away, 1)},
            },
            "prediction_settled": settled,
        }

    @mcp.tool
    def seed_recent_friendlies() -> dict:
        """Backfill match_history.json with recently-finished friendlies involving World Cup teams.

        Scans the ~3-day API-Football date window around today (the only
        window the free plan allows) for finished matches involving a World
        Cup team, and records each one (with its competition, for
        form.py's competition-weighted average) using eloratings.net for
        pre-match ratings. Safe to call repeatedly: already-recorded
        fixtures are skipped.
        """
        try:
            return seed_history.seed_recent_friendlies()
        except Exception as exc:
            return {"error": str(exc)}

    @mcp.tool
    def get_tournament_status() -> dict:
        """Return a summary of recorded predictions: played, pending, and per-group breakdown."""
        records = _load_predictions()
        if not records:
            return {"total": 0, "played": 0, "pending": 0, "groups": {}}

        played = [r for r in records if r["result"]]
        pending = [r for r in records if not r["result"]]

        groups: dict[str, dict] = {}
        for rec in records:
            grp = data.group_of(rec["home"]) or "?"
            if grp not in groups:
                groups[grp] = {"played": 0, "pending": 0}
            if rec["result"]:
                groups[grp]["played"] += 1
            else:
                groups[grp]["pending"] += 1

        return {
            "total": len(records),
            "played": len(played),
            "pending": len(pending),
            "groups": dict(sorted(groups.items())),
        }
