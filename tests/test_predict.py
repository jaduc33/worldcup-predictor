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


def test_predict_exact_score_is_a_valid_scoreline():
    result = _predict("France", "Brazil")
    home, away = result["exact_score"].split("-")
    assert int(home) >= 0
    assert int(away) >= 0
    assert len(result["top_scores"]) == 3


def test_predict_unknown_team_raises_keyerror():
    with pytest.raises(KeyError):
        _predict("Atlantis", "Brazil")


def test_predict_h2h_applied_false_by_default():
    result = _predict("France", "Brazil")
    assert result["h2h_applied"] is False


def test_predict_with_h2h_falls_back_gracefully_without_api_key(monkeypatch):
    from server.core.football_api import APIFootballError
    from server.tools import predict as predict_module

    def _raise(*args, **kwargs):
        raise APIFootballError("API_FOOTBALL_KEY is not set.")

    monkeypatch.setattr(predict_module.api, "head_to_head", _raise)

    result = _predict("France", "Brazil", use_h2h=True)
    assert result["h2h_applied"] is False
    assert sum(result["probabilities"].values()) == pytest.approx(1.0, abs=1e-2)
