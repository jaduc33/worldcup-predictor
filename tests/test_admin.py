"""Tests for server/tools/admin.py: post-match Elo updates and match history.

Ratings, predictions, and match history files are all redirected to tmp_path,
so these never touch the real data/ files.
"""

import json

import pytest
from fastmcp import FastMCP

from server.core import data
from server.tools import admin
from tests._helpers import call_tool


@pytest.fixture
def mcp_app(tmp_path, monkeypatch):
    real_ratings = dict(data.load_ratings())

    monkeypatch.setattr(admin, "_PREDICTIONS_FILE", tmp_path / "predictions.json")
    monkeypatch.setattr(data, "RATINGS_FILE", tmp_path / "elo_ratings.json")
    monkeypatch.setattr(data, "HISTORY_FILE", tmp_path / "match_history.json")

    (tmp_path / "elo_ratings.json").write_text(
        json.dumps({"ratings": real_ratings, "source": "test"}), encoding="utf-8"
    )
    data.load_ratings.cache_clear()
    data.load_match_history.cache_clear()

    mcp = FastMCP("test")
    admin.register(mcp)
    yield mcp

    data.load_ratings.cache_clear()
    data.load_match_history.cache_clear()


def test_update_match_result_appends_match_history(mcp_app):
    result = call_tool(mcp_app, "update_match_result",
                        {"home": "France", "away": "Brazil", "score_home": 2, "score_away": 1})
    assert result["outcome"] == "home_win"

    history = data.load_match_history()
    assert len(history) == 1
    entry = history[0]
    assert entry["home"] == "France"
    assert entry["away"] == "Brazil"
    assert entry["score_home"] == 2
    assert entry["score_away"] == 1
    assert entry["outcome"] == "home_win"
    assert entry["competition"] == "World Cup"
    assert "rating_home_pre" in entry and "rating_away_pre" in entry


def test_update_match_result_updates_elo_ratings(mcp_app):
    before = data.rating_of("France")
    call_tool(mcp_app, "update_match_result",
              {"home": "France", "away": "Brazil", "score_home": 2, "score_away": 1})
    after = data.rating_of("France")
    assert after > before


def test_seed_recent_friendlies_delegates_to_seed_history(mcp_app, monkeypatch):
    monkeypatch.setattr(admin.seed_history, "seed_recent_friendlies", lambda: {"added": 2, "matches": []})
    result = call_tool(mcp_app, "seed_recent_friendlies", {})
    assert result == {"added": 2, "matches": []}


def test_seed_recent_friendlies_returns_error_on_exception(mcp_app, monkeypatch):
    def _raise():
        raise RuntimeError("boom")

    monkeypatch.setattr(admin.seed_history, "seed_recent_friendlies", _raise)
    result = call_tool(mcp_app, "seed_recent_friendlies", {})
    assert "error" in result
