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
