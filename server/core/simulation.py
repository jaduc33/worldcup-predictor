"""Monte Carlo group-stage simulation: simulate each group's 6 matches N times
(sampling outcome + scoreline), build the final table per the OFFICIAL tiebreak
order (points, GD, GF -- ties beyond that broken randomly per iteration, since
fair-play and the draw of lots aren't modelled), and tally qualification rates.

Kept separate from standings.py's expected-value projection
(project_group_table), which remains the default/cheap projection. Monte Carlo
is additive and opt-in.
"""

import random
from math import exp

from server.core import data, elo
from server.core import ratings_effective as reff
from server.core.config import MAX_GOALS, MONTE_CARLO_ITERATIONS


def _poisson_sample(lam: float) -> int:
    """Knuth's algorithm: sample from Poisson(lam) using only random.random().

    Capped at MAX_GOALS + 1 draws to bound runtime for pathological lambdas
    (lam is always small here, ~0.3-4.0, so this almost never triggers).
    """
    limit = exp(-lam)
    k, p = 0, 1.0
    while True:
        k += 1
        p *= random.random()
        if p <= limit or k > MAX_GOALS + 1:
            return k - 1


def _sample_score(rating_a: float, rating_b: float, advantage: float) -> tuple[int, int]:
    lambda_a, lambda_b = elo.expected_goals(rating_a, rating_b, advantage=advantage)
    return _poisson_sample(lambda_a), _poisson_sample(lambda_b)


def _precompute_fixture_params() -> dict[str, list[tuple[str, str, float, float, float]]]:
    """Precompute (home, away, rating_home, rating_away, advantage) for every
    group's 6 fixtures, once, before the simulation loop.
    """
    out = {}
    for g, teams in data.load_groups().items():
        fx_params = []
        for fx in data.group_fixtures(g):
            home, away = fx["home"], fx["away"]
            rh = reff.effective_rating(home)
            ra = reff.effective_rating(away)
            adv = reff.effective_advantage(home, away)
            fx_params.append((home, away, rh, ra, adv))
        out[g] = fx_params
    return out


def _simulate_group_once(fx_params: list[tuple]) -> tuple[list[str], dict[str, dict]]:
    """Simulate one playthrough of a group's 6 fixtures.

    Returns (ordering 1st..4th, table stats per team) where ordering follows
    the official tiebreak (points, GD, GF desc), with totally-tied teams
    shuffled randomly first (proxy for fair-play/lots, not modelled precisely).
    """
    table: dict[str, dict] = {}
    for home, away, rh, ra, adv in fx_params:
        table.setdefault(home, {"points": 0, "gf": 0, "ga": 0})
        table.setdefault(away, {"points": 0, "gf": 0, "ga": 0})

        score_home, score_away = _sample_score(rh, ra, adv)
        table[home]["gf"] += score_home
        table[home]["ga"] += score_away
        table[away]["gf"] += score_away
        table[away]["ga"] += score_home

        if score_home > score_away:
            table[home]["points"] += 3
        elif score_home < score_away:
            table[away]["points"] += 3
        else:
            table[home]["points"] += 1
            table[away]["points"] += 1

    teams = list(table)
    random.shuffle(teams)
    teams.sort(
        key=lambda t: (table[t]["points"], table[t]["gf"] - table[t]["ga"], table[t]["gf"]),
        reverse=True,
    )
    return teams, table


def _rank_thirds(thirds: list[tuple[str, dict]]) -> list[str]:
    """thirds: list of (team, table_stats). Returns team names ranked
    best-to-worst by (points, gd, gf), ties broken randomly.
    """
    shuffled = list(thirds)
    random.shuffle(shuffled)
    shuffled.sort(
        key=lambda x: (x[1]["points"], x[1]["gf"] - x[1]["ga"], x[1]["gf"]),
        reverse=True,
    )
    return [team for team, _ in shuffled]


def run_simulation(iterations: int = MONTE_CARLO_ITERATIONS, seed: int | None = None) -> dict:
    """Run `iterations` full group-stage simulations and tally, per team:
    P(1st), P(2nd), P(3rd), P(4th), P(qualify via top-2), P(qualify via best
    third), and overall P(qualify) for the round of 32.
    """
    if seed is not None:
        random.seed(seed)

    groups = data.load_groups()
    teams = data.all_teams()
    fixture_params = _precompute_fixture_params()
    counts = {t: {"rank1": 0, "rank2": 0, "rank3": 0, "rank4": 0, "best_third": 0} for t in teams}

    for _ in range(iterations):
        thirds_this_iter = []
        for g in groups:
            order, table = _simulate_group_once(fixture_params[g])
            for rank, team in enumerate(order, start=1):
                counts[team][f"rank{rank}"] += 1
            third_team = order[2]
            thirds_this_iter.append((third_team, table[third_team]))

        for team in _rank_thirds(thirds_this_iter)[:8]:
            counts[team]["best_third"] += 1

    results = {}
    for t in teams:
        c = counts[t]
        qualify_top2 = c["rank1"] + c["rank2"]
        results[t] = {
            "team": t,
            "group": data.group_of(t),
            "p_first": round(c["rank1"] / iterations, 4),
            "p_second": round(c["rank2"] / iterations, 4),
            "p_third": round(c["rank3"] / iterations, 4),
            "p_fourth": round(c["rank4"] / iterations, 4),
            "p_qualify_top2": round(qualify_top2 / iterations, 4),
            "p_qualify_best_third": round(c["best_third"] / iterations, 4),
            "p_qualify": round((qualify_top2 + c["best_third"]) / iterations, 4),
        }
    return {"iterations": iterations, "teams": results}
