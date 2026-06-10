"""Prediction core: Elo ratings -> 1X2 probabilities and exact-score probabilities.

This is intentionally simple and SWAPPABLE. The 1X2 target keeps the maths light
so the project's energy goes into the agent/MCP architecture. Tunable parameters
live in server/core/config.py (env-var overridable) -- once real group-stage
results come in, DRAW_BASE (and any venue advantage) can be calibrated by minimising
RPS on actual matches -- see server/tools/evaluate.py.
"""

from math import exp, factorial

from server.core.config import (
    AVG_GOALS,
    DRAW_BASE,
    GOAL_RATING_SCALE,
    HOME_ADV,
    K_FACTOR,
    MAX_GOALS,
    PENALTY_SKILL_WEIGHT,
)


def win_expectancy(rating_a: float, rating_b: float, advantage: float = 0.0) -> float:
    """Classic Elo win expectancy of A vs B (blends win + half a draw)."""
    dr = (rating_a + advantage) - rating_b
    return 1.0 / (1.0 + 10 ** (-dr / 400.0))


def match_probabilities(
    rating_a: float,
    rating_b: float,
    advantage: float = HOME_ADV,
    draw_base: float = DRAW_BASE,
) -> dict:
    """Return {'win', 'draw', 'loss'} probabilities for team A vs team B.

    Win expectancy We = P(win) + 0.5 * P(draw). We model the draw as peaking when
    the teams are even and shrinking towards 0 as the mismatch grows, then back out
    win/loss. Probabilities are clamped non-negative and renormalised.
    """
    we = win_expectancy(rating_a, rating_b, advantage)
    p_draw = draw_base * (1.0 - abs(2 * we - 1.0))
    p_win = max(we - 0.5 * p_draw, 0.0)
    p_loss = max((1.0 - we) - 0.5 * p_draw, 0.0)
    total = p_win + p_draw + p_loss
    return {"win": p_win / total, "draw": p_draw / total, "loss": p_loss / total}


def update_ratings(
    rating_home: float,
    rating_away: float,
    score_home: int,
    score_away: int,
    k: float = K_FACTOR,
) -> tuple[float, float]:
    """Return (new_home_rating, new_away_rating) after a match result.

    Uses a goal-difference multiplier (FIFA-style) so a 3-0 moves ratings
    more than a 1-0, reflecting the strength of the performance.
    """
    result = 1.0 if score_home > score_away else (0.5 if score_home == score_away else 0.0)
    expected = win_expectancy(rating_home, rating_away)

    gdiff = abs(score_home - score_away)
    if gdiff <= 1:
        mult = 1.0
    elif gdiff == 2:
        mult = 1.5
    elif gdiff == 3:
        mult = 1.75
    else:
        mult = 1.75 + (gdiff - 3) / 8.0

    delta = k * mult * (result - expected)
    return round(rating_home + delta, 1), round(rating_away - delta, 1)


def expected_goals(rating_a: float, rating_b: float, advantage: float = 0.0) -> tuple[float, float]:
    """Return (lambda_a, lambda_b): each side's expected goals for a Poisson scoreline model.

    A `GOAL_RATING_SCALE`-point rating edge doubles a team's expected goals and
    halves the opponent's, while two evenly-matched teams both get AVG_GOALS.
    """
    dr = (rating_a + advantage) - rating_b
    factor = 10 ** (dr / (2 * GOAL_RATING_SCALE))
    return AVG_GOALS * factor, AVG_GOALS / factor


def score_matrix(lambda_a: float, lambda_b: float, max_goals: int = MAX_GOALS) -> dict[tuple[int, int], float]:
    """Return P(score = (i, j)) for i, j in [0, max_goals], assuming independent Poisson goals."""
    pmf_a = [exp(-lambda_a) * lambda_a ** i / factorial(i) for i in range(max_goals + 1)]
    pmf_b = [exp(-lambda_b) * lambda_b ** j / factorial(j) for j in range(max_goals + 1)]
    return {(i, j): pa * pb for i, pa in enumerate(pmf_a) for j, pb in enumerate(pmf_b)}


def most_likely_scores(lambda_a: float, lambda_b: float, top_n: int = 3, max_goals: int = MAX_GOALS) -> list[dict]:
    """Return the `top_n` most probable home-away scorelines, normalised over the grid."""
    matrix = score_matrix(lambda_a, lambda_b, max_goals)
    total = sum(matrix.values())
    ranked = sorted(matrix.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    return [{"score": f"{i}-{j}", "probability": round(p / total, 3)} for (i, j), p in ranked]


def expected_score(lambda_a: float, lambda_b: float, max_goals: int = MAX_GOALS) -> str:
    """Return each side's expected goals rounded to the nearest integer, e.g. "2-1".

    Unlike most_likely_scores' top entry (the joint mode of two independent
    Poisson distributions, which collapses to N-0/0-N/1-1 once the sides
    diverge), this rounds each mean independently and so can land on
    scorelines like 2-1 or 3-2 for moderately one-sided matchups. Clamped to
    max_goals to stay within the same grid most_likely_scores uses.
    """
    return f"{min(round(lambda_a), max_goals)}-{min(round(lambda_b), max_goals)}"


def advance_probability(rating_a: float, rating_b: float, advantage: float = 0.0) -> float:
    """P(team A advances) in a single-elimination match: regulation result, draws go to penalties.

    A penalty shootout is mostly luck, but the stronger side gets a small edge:
    PENALTY_SKILL_WEIGHT controls how much win-expectancy carries over to the shootout.
    """
    p = match_probabilities(rating_a, rating_b, advantage)
    we = win_expectancy(rating_a, rating_b, advantage)
    pen_a = 0.5 + (we - 0.5) * PENALTY_SKILL_WEIGHT
    return p["win"] + p["draw"] * pen_a
