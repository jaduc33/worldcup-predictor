"""Tests for server/core/elo.py: the 1X2 + exact-score prediction model."""

import pytest

from server.core import elo
from server.core.config import AVG_GOALS, DRAW_BASE, MAX_GOALS


def test_win_expectancy_equal_ratings_is_half():
    assert elo.win_expectancy(1900, 1900) == pytest.approx(0.5)


def test_win_expectancy_higher_rating_is_favored():
    assert elo.win_expectancy(2100, 1900) > 0.5
    assert elo.win_expectancy(1900, 2100) < 0.5


def test_match_probabilities_sum_to_one_and_non_negative():
    p = elo.match_probabilities(2100, 1900)
    assert sum(p.values()) == pytest.approx(1.0)
    assert all(v >= 0 for v in p.values())


def test_match_probabilities_equal_ratings_uses_draw_base():
    p = elo.match_probabilities(1900, 1900)
    assert p["draw"] == pytest.approx(DRAW_BASE)
    assert p["win"] == pytest.approx(p["loss"])


def test_match_probabilities_swapping_teams_swaps_win_and_loss():
    p = elo.match_probabilities(2100, 1900)
    q = elo.match_probabilities(1900, 2100)
    assert p["win"] == pytest.approx(q["loss"])
    assert p["loss"] == pytest.approx(q["win"])
    assert p["draw"] == pytest.approx(q["draw"])


def test_update_ratings_winner_gains_loser_loses():
    new_home, new_away = elo.update_ratings(1900, 1900, 2, 0)
    assert new_home > 1900
    assert new_away < 1900
    assert (new_home - 1900) == pytest.approx(-(new_away - 1900), abs=0.05)


def test_update_ratings_draw_between_equal_teams_does_not_move():
    new_home, new_away = elo.update_ratings(1900, 1900, 1, 1)
    assert new_home == pytest.approx(1900)
    assert new_away == pytest.approx(1900)


def test_update_ratings_bigger_margin_moves_more():
    _, away_after_1_0 = elo.update_ratings(1900, 1900, 1, 0)
    _, away_after_3_0 = elo.update_ratings(1900, 1900, 3, 0)
    assert away_after_3_0 < away_after_1_0


def test_expected_goals_equal_ratings_both_average():
    lh, la = elo.expected_goals(1900, 1900)
    assert lh == pytest.approx(AVG_GOALS)
    assert la == pytest.approx(AVG_GOALS)


def test_expected_goals_stronger_team_scores_more():
    lh, la = elo.expected_goals(2100, 1900)
    assert lh > AVG_GOALS > la


def test_score_matrix_is_a_valid_distribution():
    matrix = elo.score_matrix(1.25, 1.25)
    assert len(matrix) == (MAX_GOALS + 1) ** 2
    assert all(0 <= v <= 1 for v in matrix.values())
    # the truncated grid still captures almost all of the probability mass
    assert sum(matrix.values()) > 0.99


def test_most_likely_scores_for_equal_teams_is_1_1():
    top = elo.most_likely_scores(AVG_GOALS, AVG_GOALS, top_n=3)
    assert top[0]["score"] == "1-1"


def test_most_likely_scores_are_ranked_descending():
    top = elo.most_likely_scores(2.0, 0.8, top_n=5)
    probs = [s["probability"] for s in top]
    assert probs == sorted(probs, reverse=True)


def test_advance_probability_equal_ratings_is_half():
    assert elo.advance_probability(1900, 1900) == pytest.approx(0.5)


def test_advance_probability_is_complementary_and_favors_stronger_team():
    a = elo.advance_probability(2100, 1900)
    b = elo.advance_probability(1900, 2100)
    assert a + b == pytest.approx(1.0)
    assert a > 0.5
