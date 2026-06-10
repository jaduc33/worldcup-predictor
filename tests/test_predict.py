"""Tests for server/tools/predict.py: 1X2 + exact-score predictions."""

import pytest

from server.tools.predict import _predict


def test_predict_structure_and_probabilities_sum_to_one():
    result = _predict("France", "Brazil")
    probs = result["probabilities"]
    assert set(probs) == {"home_win", "draw", "away_win"}
    assert sum(probs.values()) == pytest.approx(1.0, abs=1e-2)


def test_predict_pick_is_argmax_of_probabilities():
    result = _predict("France", "Brazil")
    probs = result["probabilities"]
    assert result["pick"] == max(probs, key=probs.get)


def test_predict_exact_score_matches_top_scores_first_entry():
    result = _predict("France", "Brazil")
    assert result["exact_score"] == result["top_scores"][0]["score"]
    assert len(result["top_scores"]) == 3


def test_predict_unknown_team_raises_keyerror():
    with pytest.raises(KeyError):
        _predict("Atlantis", "Brazil")
