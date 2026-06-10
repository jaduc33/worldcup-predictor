"""Tests for server/tools/evaluate.py: prediction storage, settlement, and scoring.

`evaluate.STORE` is monkeypatched to a temp file for every test in this module,
so these never touch the real data/predictions.json.
"""

import pytest
from fastmcp import FastMCP

from server.tools import evaluate
from tests._helpers import call_tool


def test_rps_perfect_prediction_is_zero():
    probs = {"home_win": 1.0, "draw": 0.0, "away_win": 0.0}
    assert evaluate._rps(probs, "home_win") == pytest.approx(0.0)


def test_rps_worst_case_is_one():
    probs = {"home_win": 1.0, "draw": 0.0, "away_win": 0.0}
    assert evaluate._rps(probs, "away_win") == pytest.approx(1.0)


def test_rps_penalizes_far_misses_more_than_near_misses():
    probs = {"home_win": 1.0, "draw": 0.0, "away_win": 0.0}
    near_miss = evaluate._rps(probs, "draw")
    far_miss = evaluate._rps(probs, "away_win")
    assert near_miss < far_miss


@pytest.fixture
def mcp_app(tmp_path, monkeypatch):
    monkeypatch.setattr(evaluate, "STORE", tmp_path / "predictions.json")
    mcp = FastMCP("test")
    evaluate.register(mcp)
    return mcp


def test_record_predict_settle_and_score_roundtrip(mcp_app):
    recorded = call_tool(mcp_app, "record_prediction", {"home": "France", "away": "Brazil"})
    assert recorded["stored"] is True
    assert recorded["index"] == 0
    assert set(recorded["probabilities"]) == {"home_win", "draw", "away_win"}
    assert "exact_score" in recorded

    settled = call_tool(mcp_app, "record_result", {"home": "France", "away": "Brazil", "outcome": "home_win"})
    assert settled["updated"] is True

    accuracy = call_tool(mcp_app, "get_accuracy")
    assert accuracy["settled"] == 1
    for key in ("rps", "brier", "log_loss", "hit_rate"):
        assert key in accuracy


def test_record_result_rejects_invalid_outcome(mcp_app):
    call_tool(mcp_app, "record_prediction", {"home": "France", "away": "Brazil"})
    result = call_tool(mcp_app, "record_result", {"home": "France", "away": "Brazil", "outcome": "bogus"})
    assert "error" in result


def test_record_result_with_no_open_prediction_returns_error(mcp_app):
    result = call_tool(mcp_app, "record_result", {"home": "France", "away": "Brazil", "outcome": "home_win"})
    assert "error" in result


def test_get_accuracy_with_no_predictions_returns_zero_settled(mcp_app):
    result = call_tool(mcp_app, "get_accuracy")
    assert result["settled"] == 0
