"""Tests for server/core/h2h.py: head-to-head probability blending."""

import pytest

from server.core import h2h
from server.core.config import H2H_MIN_MATCHES


def test_h2h_probabilities_returns_none_below_min_matches():
    matches = [{"home": "France", "away": "Brazil", "score": "2-1"}] * (H2H_MIN_MATCHES - 1)
    assert h2h.h2h_probabilities(matches, team_a="France") is None


def test_h2h_probabilities_perspective_normalized():
    matches = [
        {"home": "France", "away": "Brazil", "score": "2-1"},  # France win
        {"home": "Brazil", "away": "France", "score": "0-0"},  # draw
        {"home": "France", "away": "Brazil", "score": "0-1"},  # France loss
    ]
    result = h2h.h2h_probabilities(matches, team_a="France")
    assert result is not None
    assert set(result) == {"win", "draw", "loss"}
    assert sum(result.values()) == pytest.approx(1.0)
    assert result["win"] > 0
    assert result["draw"] > 0
    assert result["loss"] > 0


def test_h2h_probabilities_ignores_matches_without_score():
    matches = [
        {"home": "France", "away": "Brazil", "score": "2-1"},
        {"home": "France", "away": "Brazil", "score": "1-1"},
        {"home": "France", "away": "Brazil", "score": None},
    ]
    assert h2h.h2h_probabilities(matches, team_a="France") is None


def test_blend_probabilities_returns_elo_unchanged_when_h2h_none():
    elo_probs = {"win": 0.5, "draw": 0.3, "loss": 0.2}
    assert h2h.blend_probabilities(elo_probs, None) == elo_probs


def test_blend_probabilities_sums_to_one_and_moves_toward_h2h():
    elo_probs = {"win": 0.2, "draw": 0.3, "loss": 0.5}
    h2h_probs = {"win": 1.0, "draw": 0.0, "loss": 0.0}
    blended = h2h.blend_probabilities(elo_probs, h2h_probs)
    assert sum(blended.values()) == pytest.approx(1.0)
    assert blended["win"] > elo_probs["win"]
    assert blended["loss"] < elo_probs["loss"]
