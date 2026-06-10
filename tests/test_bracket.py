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
