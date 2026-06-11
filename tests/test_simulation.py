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


def test_run_tournament_simulation_result_structure():
    result = simulation.run_tournament_simulation(iterations=200, seed=42)
    assert result["iterations"] == 200
    assert set(result["teams"]) == set(data.all_teams())

    for team_result in result["teams"].values():
        for key in ("p_qualify", "p_round_of_16", "p_quarterfinals",
                     "p_semifinals", "p_final", "p_champion", "p_third_place_match"):
            assert 0.0 <= team_result[key] <= 1.0


def test_run_tournament_simulation_stage_probabilities_are_monotonic():
    result = simulation.run_tournament_simulation(iterations=200, seed=42)
    for team_result in result["teams"].values():
        assert team_result["p_champion"] <= team_result["p_final"]
        assert team_result["p_final"] <= team_result["p_semifinals"]
        assert team_result["p_semifinals"] <= team_result["p_quarterfinals"]
        assert team_result["p_quarterfinals"] <= team_result["p_round_of_16"]
        assert team_result["p_round_of_16"] <= team_result["p_qualify"]


def test_run_tournament_simulation_stage_totals():
    result = simulation.run_tournament_simulation(iterations=500, seed=42)
    teams = result["teams"].values()
    assert sum(t["p_champion"] for t in teams) == pytest.approx(1.0, abs=0.01)
    assert sum(t["p_final"] for t in teams) == pytest.approx(2.0, abs=0.01)
    assert sum(t["p_semifinals"] for t in teams) == pytest.approx(4.0, abs=0.01)
    assert sum(t["p_quarterfinals"] for t in teams) == pytest.approx(8.0, abs=0.01)
    assert sum(t["p_round_of_16"] for t in teams) == pytest.approx(16.0, abs=0.01)
    assert sum(t["p_third_place_match"] for t in teams) == pytest.approx(2.0, abs=0.01)


def test_run_tournament_simulation_reproducible_with_seed():
    result1 = simulation.run_tournament_simulation(iterations=100, seed=123)
    result2 = simulation.run_tournament_simulation(iterations=100, seed=123)
    assert result1 == result2
