"""Tests for server/core/form.py: recency-weighted form adjustment."""

import pytest

from server.core import form
from server.core.config import FORM_MAX_ADJUSTMENT, FRIENDLY_FORM_WEIGHT


def test_no_history_returns_zero():
    assert form.team_form_adjustment("France", history=[]) == 0.0


def test_single_match_returns_zero():
    history = [
        {"home": "France", "away": "Brazil", "score_home": 2, "score_away": 0,
         "rating_home_pre": 1900.0, "rating_away_pre": 2100.0, "outcome": "home_win"},
    ]
    assert form.team_form_adjustment("France", history=history) == 0.0


def test_overperformance_yields_positive_adjustment():
    history = [
        {"home": "France", "away": "Brazil", "score_home": 3, "score_away": 0,
         "rating_home_pre": 1900.0, "rating_away_pre": 2100.0, "outcome": "home_win"},
        {"home": "Argentina", "away": "France", "score_home": 0, "score_away": 2,
         "rating_home_pre": 2100.0, "rating_away_pre": 1900.0, "outcome": "away_win"},
    ]
    assert form.team_form_adjustment("France", history=history) > 0.0


def test_underperformance_yields_negative_adjustment():
    history = [
        {"home": "France", "away": "Brazil", "score_home": 0, "score_away": 3,
         "rating_home_pre": 2100.0, "rating_away_pre": 1900.0, "outcome": "away_win"},
        {"home": "Argentina", "away": "France", "score_home": 2, "score_away": 0,
         "rating_home_pre": 1900.0, "rating_away_pre": 2100.0, "outcome": "home_win"},
    ]
    assert form.team_form_adjustment("France", history=history) < 0.0


def test_adjustment_is_capped_at_form_max_adjustment():
    history = [
        {"home": "France", "away": "Brazil", "score_home": 6, "score_away": 0,
         "rating_home_pre": 1500.0, "rating_away_pre": 2300.0, "outcome": "home_win"},
    ] * 5
    adjustment = form.team_form_adjustment("France", history=history)
    assert adjustment == pytest.approx(FORM_MAX_ADJUSTMENT)


def test_match_weight_friendly_vs_competitive():
    assert form._match_weight({"competition": "Friendlies"}) == FRIENDLY_FORM_WEIGHT
    assert form._match_weight({"competition": "World Cup"}) == 1.0
    assert form._match_weight({}) == 1.0


def _match(home, away, score_home, score_away, r_home=1900.0, r_away=1900.0, stats=None):
    entry = {"home": home, "away": away, "score_home": score_home, "score_away": score_away,
             "rating_home_pre": r_home, "rating_away_pre": r_away,
             "outcome": "home_win" if score_home > score_away else ("draw" if score_home == score_away else "away_win")}
    if stats:
        entry["stats"] = stats
    return entry


def test_stats_shots_on_target_dominance_boosts_form():
    """Dominating in SOT beyond what Elo expects should yield a higher form than no stats."""
    base = _match("France", "Brazil", 1, 0)
    with_sot = _match("France", "Brazil", 1, 0,
                       stats={"home": {"shots_on_target": 10, "xg": None},
                               "away": {"shots_on_target": 2, "xg": None}})
    history_no_stats = [base, base]
    history_with_stats = [with_sot, with_sot]
    assert form.team_form_adjustment("France", history=history_with_stats) > \
           form.team_form_adjustment("France", history=history_no_stats)


def test_stats_xg_dominance_boosts_form():
    """High xG for + low xG against beyond expectation should boost form."""
    base = _match("France", "Brazil", 1, 0)
    with_xg = _match("France", "Brazil", 1, 0,
                      stats={"home": {"shots_on_target": None, "xg": 3.0},
                              "away": {"shots_on_target": None, "xg": 0.3}})
    history_no_stats = [base, base]
    history_with_xg = [with_xg, with_xg]
    assert form.team_form_adjustment("France", history=history_with_xg) > \
           form.team_form_adjustment("France", history=history_no_stats)


def test_stats_missing_fields_do_not_crash():
    """Partial or empty stats dicts should not raise errors."""
    history = [
        _match("France", "Brazil", 2, 1, stats={"home": {}, "away": {}}),
        _match("France", "Brazil", 2, 1, stats={"home": {}, "away": {}}),
    ]
    result = form.team_form_adjustment("France", history=history)
    assert isinstance(result, float)


def test_friendly_results_count_less_than_competitive_in_mixed_history():
    overperformance = {"home": "France", "away": "Brazil", "score_home": 6, "score_away": 0,
                        "rating_home_pre": 1500.0, "rating_away_pre": 2300.0, "outcome": "home_win"}
    neutral = {"home": "Argentina", "away": "France", "score_home": 0, "score_away": 0,
               "rating_home_pre": 1900.0, "rating_away_pre": 1900.0, "outcome": "draw"}

    friendly_then_neutral = [dict(overperformance, competition="Friendlies"), neutral]
    competitive_then_neutral = [dict(overperformance, competition="World Cup"), neutral]

    adj_friendly = form.team_form_adjustment("France", history=friendly_then_neutral)
    adj_competitive = form.team_form_adjustment("France", history=competitive_then_neutral)

    assert adj_friendly < adj_competitive
