"""Tests for server/core/simulation.py: Monte Carlo group-stage simulation."""

import pytest

from server.core import data, simulation


def test_poisson_sample_mean_approximates_lambda():
    lam = 1.5
    n = 20000
    samples = [simulation._poisson_sample(lam) for _ in range(n)]
    mean = sum(samples) / n
    assert mean == pytest.approx(lam, abs=0.05)


def test_run_simulation_result_structure():
    result = simulation.run_simulation(iterations=200, seed=42)
    assert result["iterations"] == 200
    assert set(result["teams"]) == set(data.all_teams())

    for team_result in result["teams"].values():
        for key in ("p_first", "p_second", "p_third", "p_fourth",
                     "p_qualify_top2", "p_qualify_best_third", "p_qualify"):
            assert 0.0 <= team_result[key] <= 1.0


def test_run_simulation_per_group_first_place_probabilities_sum_to_one():
    result = simulation.run_simulation(iterations=200, seed=42)
    for teams in data.load_groups().values():
        total_first = sum(result["teams"][t]["p_first"] for t in teams)
        assert total_first == pytest.approx(1.0, abs=1e-6)


def test_run_simulation_best_third_total_approximates_eight():
    result = simulation.run_simulation(iterations=500, seed=42)
    total = sum(t["p_qualify_best_third"] for t in result["teams"].values())
    assert total == pytest.approx(8.0, abs=0.5)


def test_run_simulation_qualify_is_sum_of_top2_and_best_third():
    result = simulation.run_simulation(iterations=200, seed=42)
    for team_result in result["teams"].values():
        assert team_result["p_qualify"] == pytest.approx(
            team_result["p_qualify_top2"] + team_result["p_qualify_best_third"], abs=1e-6
        )
