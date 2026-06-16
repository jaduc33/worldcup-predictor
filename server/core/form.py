"""Recency-weighted "form" adjustment: a temporary rating bonus/malus reflecting
a team's last few results vs Elo-expectation, used ONLY at prediction time --
never persisted into elo_ratings.json (that's elo.update_ratings' job).

Degrades to 0.0 (no adjustment) until enough match_history.json entries exist,
which is the case for the whole tournament until update_match_result() has
been called at least twice for a given team.

Each match_history.json entry may carry a "competition" field (the
API-Football league name, e.g. "Friendlies" or "World Cup"). Friendlies count
less toward form than competitive matches -- different stakes and lineups make
them less representative of a team's "real" current level.
"""

from server.core import elo
from server.core.config import FORM_MAX_ADJUSTMENT, FORM_WEIGHT, FORM_WINDOW, FRIENDLY_FORM_WEIGHT

_FRIENDLY_COMPETITIONS = {"Friendlies"}


def _match_weight(entry: dict) -> float:
    return FRIENDLY_FORM_WEIGHT if entry.get("competition") in _FRIENDLY_COMPETITIONS else 1.0


def _match_form_score(entry: dict, team: str) -> float:
    """One match's form contribution for `team`: actual points minus
    Elo-expected points, plus a smaller goal-difference-vs-expectation term.
    """
    is_home = entry["home"] == team
    rating_for = entry["rating_home_pre"] if is_home else entry["rating_away_pre"]
    rating_against = entry["rating_away_pre"] if is_home else entry["rating_home_pre"]
    score_for = entry["score_home"] if is_home else entry["score_away"]
    score_against = entry["score_away"] if is_home else entry["score_home"]

    actual_points = 3.0 if score_for > score_against else (1.0 if score_for == score_against else 0.0)
    expected_points = 3.0 * elo.win_expectancy(rating_for, rating_against)
    points_term = actual_points - expected_points

    goals_for, goals_against = elo.expected_goals(rating_for, rating_against)
    gd_term = (score_for - score_against) - (goals_for - goals_against)

    score = points_term + 0.3 * gd_term

    # Shots-on-target term: did the team create more/fewer chances than Elo predicts?
    stats = entry.get("stats")
    if stats:
        side = "home" if is_home else "away"
        opp = "away" if is_home else "home"
        sot_for = (stats.get(side) or {}).get("shots_on_target")
        sot_against = (stats.get(opp) or {}).get("shots_on_target")
        if sot_for is not None and sot_against is not None:
            total_sot = sot_for + sot_against
            if total_sot > 0:
                actual_ratio = sot_for / total_sot
                expected_ratio = elo.win_expectancy(rating_for, rating_against)
                score += 0.5 * (actual_ratio - expected_ratio)

    return score


def team_form_adjustment(team: str, history: list[dict] | None = None) -> float:
    """Return a small Elo-point adjustment for `team` based on its last
    FORM_WINDOW matches in match_history.json. 0.0 if fewer than 2 matches
    are on record.
    """
    if history is None:
        from server.core import data
        history = data.load_match_history()

    team_matches = [e for e in history if e["home"] == team or e["away"] == team]
    if len(team_matches) < 2:
        return 0.0

    recent = team_matches[-FORM_WINDOW:]
    weights = [_match_weight(e) for e in recent]
    raw = sum(w * _match_form_score(e, team) for w, e in zip(weights, recent)) / sum(weights)
    adjustment = raw * FORM_WEIGHT
    return max(-FORM_MAX_ADJUSTMENT, min(FORM_MAX_ADJUSTMENT, adjustment))
