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


def _fake_wc_fixture(home: str, away: str, score_home: int, score_away: int,
                      fixture_id: int = 9000) -> dict:
    """Minimal raw API-Football fixture dict for a finished World Cup match."""
    return {
        "fixture": {
            "id": fixture_id,
            "date": "2026-06-12T21:00:00+00:00",
            "status": {"long": "Match Finished"},
        },
        "league": {"id": 1, "name": "FIFA World Cup"},
        "teams": {
            "home": {"name": home},
            "away": {"name": away},
        },
        "goals": {"home": score_home, "away": score_away},
    }


def test_seed_world_cup_results_adds_match_and_updates_elo(mcp_app, monkeypatch):
    from server.core import seed_history

    france_before = data.rating_of("France")
    brazil_before = data.rating_of("Brazil")

    fixtures = [_fake_wc_fixture("France", "Brazil", 2, 1)]
    monkeypatch.setattr(seed_history.api, "fixtures_on_date", lambda d: fixtures)
    monkeypatch.setattr(seed_history, "_dates_since_wc_start", lambda: ["2026-06-12"])

    result = call_tool(mcp_app, "seed_world_cup_results", {})

    assert result["added"] == 1
    assert result["matches"][0]["match"] == "France 2-1 Brazil"

    history = data.load_match_history()
    assert any(e["home"] == "France" and e["away"] == "Brazil" for e in history)

    assert data.rating_of("France") > france_before
    assert data.rating_of("Brazil") < brazil_before


def test_seed_world_cup_results_skips_non_wc_matches(mcp_app, monkeypatch):
    from server.core import seed_history

    non_wc = _fake_wc_fixture("France", "Brazil", 1, 0)
    non_wc["league"] = {"id": 999, "name": "Friendly"}

    monkeypatch.setattr(seed_history.api, "fixtures_on_date", lambda d: [non_wc])
    monkeypatch.setattr(seed_history, "_dates_since_wc_start", lambda: ["2026-06-12"])

    result = call_tool(mcp_app, "seed_world_cup_results", {})
    assert result["added"] == 0


def test_seed_world_cup_results_skips_duplicate_fixture(mcp_app, monkeypatch):
    from server.core import seed_history

    fixtures = [_fake_wc_fixture("France", "Brazil", 2, 1, fixture_id=9001)]
    monkeypatch.setattr(seed_history.api, "fixtures_on_date", lambda d: fixtures)
    monkeypatch.setattr(seed_history, "_dates_since_wc_start", lambda: ["2026-06-12"])

    result1 = call_tool(mcp_app, "seed_world_cup_results", {})
    assert result1["added"] == 1

    result2 = call_tool(mcp_app, "seed_world_cup_results", {})
    assert result2["added"] == 0


def test_seed_world_cup_results_stores_stats_when_available(mcp_app, monkeypatch):
    from server.core import seed_history

    fixtures = [_fake_wc_fixture("France", "Brazil", 2, 1, fixture_id=9100)]
    monkeypatch.setattr(seed_history.api, "fixtures_on_date", lambda d: fixtures)
    monkeypatch.setattr(seed_history, "_dates_since_wc_start", lambda: ["2026-06-12"])
    fake_stats = {"home": {"shots_on_target": 8, "total_shots": 14, "possession": 60, "xg": 2.1},
                  "away": {"shots_on_target": 3, "total_shots": 8, "possession": 40, "xg": 0.9}}
    monkeypatch.setattr(seed_history.api, "fixture_statistics", lambda fid: fake_stats)

    call_tool(mcp_app, "seed_world_cup_results", {})

    history = data.load_match_history()
    entry = next(e for e in history if e.get("fixture_id") == 9100)
    assert entry["stats"] == fake_stats


def test_backfill_match_stats_adds_stats_to_existing_entries(mcp_app, monkeypatch):
    from server.core import seed_history

    # Seed a match without stats
    fixtures = [_fake_wc_fixture("France", "Brazil", 2, 1, fixture_id=9200)]
    monkeypatch.setattr(seed_history.api, "fixtures_on_date", lambda d: fixtures)
    monkeypatch.setattr(seed_history, "_dates_since_wc_start", lambda: ["2026-06-12"])
    monkeypatch.setattr(seed_history.api, "fixture_statistics", lambda fid: None)
    call_tool(mcp_app, "seed_world_cup_results", {})

    # Now backfill with stats
    fake_stats = {"home": {"shots_on_target": 7, "xg": 1.8}, "away": {"shots_on_target": 4, "xg": 1.1}}
    monkeypatch.setattr(seed_history.api, "fixture_statistics", lambda fid: fake_stats)

    result = call_tool(mcp_app, "backfill_match_stats", {})
    assert result["updated"] == 1

    history = data.load_match_history()
    entry = next(e for e in history if e.get("fixture_id") == 9200)
    assert entry["stats"] == fake_stats


def test_backfill_match_stats_skips_entries_already_having_stats(mcp_app, monkeypatch):
    from server.core import seed_history

    fake_stats = {"home": {"shots_on_target": 5, "xg": 1.5}, "away": {"shots_on_target": 3, "xg": 0.8}}
    fixtures = [_fake_wc_fixture("France", "Brazil", 2, 1, fixture_id=9300)]
    monkeypatch.setattr(seed_history.api, "fixtures_on_date", lambda d: fixtures)
    monkeypatch.setattr(seed_history, "_dates_since_wc_start", lambda: ["2026-06-12"])
    monkeypatch.setattr(seed_history.api, "fixture_statistics", lambda fid: fake_stats)
    call_tool(mcp_app, "seed_world_cup_results", {})

    # Backfill should skip — stats already present
    result = call_tool(mcp_app, "backfill_match_stats", {})
    assert result["updated"] == 0


def test_seed_world_cup_results_returns_error_on_exception(mcp_app, monkeypatch):
    def _raise():
        raise RuntimeError("boom")

    monkeypatch.setattr(admin.seed_history, "seed_world_cup_results", _raise)
    result = call_tool(mcp_app, "seed_world_cup_results", {})
    assert "error" in result
