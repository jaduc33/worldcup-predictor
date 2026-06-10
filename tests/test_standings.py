"""Tests for server/core/standings.py: group-table and 3rd-place projections."""

import pytest

from server.core import data, standings


@pytest.mark.parametrize("group", sorted(data.load_groups()))
def test_project_group_table_structure(group):
    table = standings.project_group_table(group)
    assert len(table) == 4
    assert {row["team"] for row in table} == set(data.load_groups()[group])
    assert [row["rank"] for row in table] == [1, 2, 3, 4]

    # sorted by exp_points desc, tie-broken by exp_gd then exp_gf
    keys = [(row["exp_points"], row["exp_gd"], row["exp_gf"]) for row in table]
    assert keys == sorted(keys, reverse=True)


@pytest.mark.parametrize("group", sorted(data.load_groups()))
def test_group_total_expected_points_within_bounds(group):
    table = standings.project_group_table(group)
    total = sum(row["exp_points"] for row in table)
    # 6 matches, each contributing between (3 - DRAW_BASE) and 3 points combined
    assert 6 * 2.5 <= total <= 6 * 3.0


def test_rank_third_placed_orders_12_teams_and_flags_top_8():
    result = standings.project_all_groups()
    thirds = result["third_place_ranking"]

    assert len(thirds) == 12
    assert [row["third_place_rank"] for row in thirds] == list(range(1, 13))
    assert sum(row["qualifies"] for row in thirds) == 8
    assert all(row["qualifies"] for row in thirds[:8])
    assert not any(row["qualifies"] for row in thirds[8:])

    keys = [(row["exp_points"], row["exp_gd"], row["exp_gf"]) for row in thirds]
    assert keys == sorted(keys, reverse=True)


def test_project_all_groups_covers_every_group():
    result = standings.project_all_groups()
    assert set(result["groups"]) == set(data.load_groups())
    assert len(result["third_place_ranking"]) == 12
