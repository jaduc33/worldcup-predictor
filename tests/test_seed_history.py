"""Tests for server/core/seed_history.py: backfill match_history.json with
recently-finished friendlies, using mocked API-Football and eloratings.net data
(no network calls)."""

import pytest

from server.core import data, seed_history

_LIVE_RATINGS = {
    "Argentina": 2115.0, "Iceland": 1450.0, "Wales": 1700.0, "Czechia": 1800.0,
}


def _fixture(home, away, score_home=None, score_away=None, status="Match Finished",
              league="Friendlies", fixture_id=1):
    return {
        "fixture": {"id": fixture_id, "date": "2026-06-10T15:00:00+00:00",
                    "status": {"long": status}, "venue": {"name": "Stadium"}},
        "league": {"name": league},
        "teams": {"home": {"name": home}, "away": {"name": away}},
        "goals": {"home": score_home, "away": score_away},
    }


@pytest.fixture
def history_file(tmp_path, monkeypatch):
    monkeypatch.setattr(data, "HISTORY_FILE", tmp_path / "match_history.json")
    data.load_match_history.cache_clear()
    yield
    data.load_match_history.cache_clear()


def test_seed_recent_friendlies_adds_finished_wc_team_match(history_file, monkeypatch):
    fixtures = [_fixture("Argentina", "Iceland", 3, 0, fixture_id=101)]
    monkeypatch.setattr(seed_history.api, "fixtures_on_date", lambda d: fixtures)
    monkeypatch.setattr(seed_history.fetch, "fetch_live_ratings", lambda: _LIVE_RATINGS)

    result = seed_history.seed_recent_friendlies(dates=["2026-06-10"])
    assert result["added"] == 1

    history = data.load_match_history()
    assert len(history) == 1
    entry = history[0]
    assert entry["home"] == "Argentina"
    assert entry["away"] == "Iceland"
    assert entry["score_home"] == 3
    assert entry["score_away"] == 0
    assert entry["outcome"] == "home_win"
    assert entry["competition"] == "Friendlies"
    assert entry["fixture_id"] == 101
    assert entry["rating_home_pre"] == _LIVE_RATINGS["Argentina"]
    assert entry["rating_away_pre"] == _LIVE_RATINGS["Iceland"]


def test_seed_recent_friendlies_skips_unfinished_matches(history_file, monkeypatch):
    fixtures = [_fixture("Argentina", "Iceland", status="First Half", fixture_id=102)]
    monkeypatch.setattr(seed_history.api, "fixtures_on_date", lambda d: fixtures)
    monkeypatch.setattr(seed_history.fetch, "fetch_live_ratings", lambda: _LIVE_RATINGS)

    result = seed_history.seed_recent_friendlies(dates=["2026-06-11"])
    assert result["added"] == 0
    assert data.load_match_history() == []


def test_seed_recent_friendlies_skips_matches_without_a_wc_team(history_file, monkeypatch):
    fixtures = [_fixture("Iceland", "Wales", 1, 1, fixture_id=103)]
    monkeypatch.setattr(seed_history.api, "fixtures_on_date", lambda d: fixtures)
    monkeypatch.setattr(seed_history.fetch, "fetch_live_ratings", lambda: _LIVE_RATINGS)

    result = seed_history.seed_recent_friendlies(dates=["2026-06-10"])
    assert result["added"] == 0
    assert data.load_match_history() == []


def test_seed_recent_friendlies_skips_already_recorded_fixture_id(history_file, monkeypatch):
    fixtures = [_fixture("Argentina", "Iceland", 3, 0, fixture_id=101)]
    monkeypatch.setattr(seed_history.api, "fixtures_on_date", lambda d: fixtures)
    monkeypatch.setattr(seed_history.fetch, "fetch_live_ratings", lambda: _LIVE_RATINGS)

    seed_history.seed_recent_friendlies(dates=["2026-06-10"])
    result = seed_history.seed_recent_friendlies(dates=["2026-06-10"])
    assert result["added"] == 0
    assert len(data.load_match_history()) == 1


def test_seed_recent_friendlies_normalizes_known_name_variants(history_file, monkeypatch):
    fixtures = [_fixture("Czech Republic", "Wales", 2, 1, league="World Cup", fixture_id=104)]
    monkeypatch.setattr(seed_history.api, "fixtures_on_date", lambda d: fixtures)
    monkeypatch.setattr(seed_history.fetch, "fetch_live_ratings", lambda: _LIVE_RATINGS)

    result = seed_history.seed_recent_friendlies(dates=["2026-06-10"])
    assert result["added"] == 1
    entry = data.load_match_history()[0]
    assert entry["home"] == "Czechia"
    assert entry["away"] == "Wales"
