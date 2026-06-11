"""Tests for server/core/bracket.py: round-of-32 slot resolution."""

import pytest

from server.core import bracket, standings


def _fake_third(group: str, rank: int) -> dict:
    return {"team": f"Team-{group}", "group": group, "third_place_rank": rank, "qualifies": True}


def test_assign_third_placed_fills_all_slots_uniquely():
    qualified = [_fake_third(g, i + 1) for i, g in enumerate("ABCDEFGH")]
    assignment = bracket.assign_third_placed(qualified)

    assert set(assignment) == set(bracket.THIRD_PLACE_SLOTS)
    teams = [row["team"] for row in assignment.values()]
    assert len(teams) == len(set(teams))


def test_assign_third_placed_respects_eligibility():
    qualified = [_fake_third(g, i + 1) for i, g in enumerate("ABCDEFGH")]
    assignment = bracket.assign_third_placed(qualified)

    for slot, row in assignment.items():
        assert row["group"] in bracket.THIRD_PLACE_SLOTS[slot]


def test_assign_third_placed_raises_with_no_candidates():
    with pytest.raises(ValueError):
        bracket.assign_third_placed([])


def test_resolve_fixtures_produces_16_matches_with_32_unique_teams():
    projection = standings.project_all_groups()
    qualified = [r for r in projection["third_place_ranking"] if r["qualifies"]]
    fixtures = bracket.resolve_fixtures(projection["groups"], qualified)

    assert len(fixtures) == 16
    teams = {fx["home"] for fx in fixtures} | {fx["away"] for fx in fixtures}
    assert len(teams) == 32
    for fx in fixtures:
        assert fx["home"] != fx["away"]


def test_resolve_round_looks_up_home_and_away_from_previous_results():
    schedule = [{"match": 100, "home": 1, "away": 2}, {"match": 101, "home": 3, "away": 4}]
    prev_results = {1: "France", 2: "Brazil", 3: "Spain", 4: "Argentina"}

    resolved = bracket.resolve_round(schedule, prev_results)

    assert resolved == [
        (schedule[0], "France", "Brazil"),
        (schedule[1], "Spain", "Argentina"),
    ]


def test_round_of_16_references_each_round_of_32_match_exactly_once():
    refs = [fx["home"] for fx in bracket.ROUND_OF_16] + [fx["away"] for fx in bracket.ROUND_OF_16]
    assert sorted(refs) == list(range(1, 17))


def test_quarterfinals_reference_each_round_of_16_match_exactly_once():
    refs = [fx["home"] for fx in bracket.QUARTERFINALS] + [fx["away"] for fx in bracket.QUARTERFINALS]
    r16_matches = [fx["match"] for fx in bracket.ROUND_OF_16]
    assert sorted(refs) == sorted(r16_matches)


def test_semifinals_reference_each_quarterfinal_match_exactly_once():
    refs = [fx["home"] for fx in bracket.SEMIFINALS] + [fx["away"] for fx in bracket.SEMIFINALS]
    qf_matches = [fx["match"] for fx in bracket.QUARTERFINALS]
    assert sorted(refs) == sorted(qf_matches)


def test_final_and_third_place_reference_both_semifinal_matches():
    sf_matches = {fx["match"] for fx in bracket.SEMIFINALS}
    assert {bracket.FINAL["home"], bracket.FINAL["away"]} == sf_matches
    assert {bracket.THIRD_PLACE["home"], bracket.THIRD_PLACE["away"]} == sf_matches
