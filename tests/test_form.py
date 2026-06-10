"""Tests for server/core/form.py: recency-weighted form adjustment."""

import pytest

from server.core import form
from server.core.config import FORM_MAX_ADJUSTMENT


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
