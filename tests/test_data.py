"""Tests for server/core/data.py: groups, ratings, and lookup helpers."""

import pytest

from server.core import data


def test_load_groups_has_12_groups_of_4_teams():
    groups = data.load_groups()
    assert len(groups) == 12
    assert all(len(teams) == 4 for teams in groups.values())


def test_all_teams_returns_48_unique_sorted_names():
    teams = data.all_teams()
    assert len(teams) == 48
    assert len(set(teams)) == 48
    assert teams == sorted(teams)


def test_group_of_known_team():
    assert data.group_of("France") == "I"


def test_group_of_unknown_team_returns_none():
    assert data.group_of("Atlantis") is None


def test_rating_of_known_team_is_a_float():
    assert isinstance(data.rating_of("France"), float)


def test_rating_of_unknown_team_raises_keyerror():
    with pytest.raises(KeyError):
        data.rating_of("Atlantis")


def test_group_fixtures_has_6_unique_round_robin_pairs():
    fixtures = data.group_fixtures("A")
    assert len(fixtures) == 6
    teams = set(data.load_groups()["A"])
    pairs = {(fx["home"], fx["away"]) for fx in fixtures}
    assert len(pairs) == 6
    for home, away in pairs:
        assert home in teams and away in teams


def test_every_team_in_a_group_has_a_rating():
    ratings = data.load_ratings()
    missing = [t for t in data.all_teams() if t not in ratings]
    assert not missing, f"Missing ratings for: {missing}"


def test_load_hosts_returns_world_cup_2026_hosts():
    assert set(data.load_hosts()) == {"USA", "Canada", "Mexico"}


def test_load_match_history_empty_when_file_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(data, "HISTORY_FILE", tmp_path / "match_history.json")
    data.load_match_history.cache_clear()
    assert data.load_match_history() == []
    data.load_match_history.cache_clear()


def test_append_match_history_persists_entries(tmp_path, monkeypatch):
    monkeypatch.setattr(data, "HISTORY_FILE", tmp_path / "match_history.json")
    data.load_match_history.cache_clear()

    entry = {
        "home": "France", "away": "Brazil", "score_home": 2, "score_away": 1,
        "rating_home_pre": 2000.0, "rating_away_pre": 1990.0, "outcome": "home_win",
    }
    data.append_match_history(entry)
    assert data.load_match_history() == [entry]

    data.load_match_history.cache_clear()
