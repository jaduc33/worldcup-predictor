"""Monte Carlo simulation: groups (and optionally the full knockout bracket).

Each iteration simulates a group's 6 matches by sampling outcome + scoreline,
builds the final table per the OFFICIAL tiebreak order (points, GD, GF -- ties
beyond that broken randomly per iteration, since fair-play and the draw of
lots aren't modelled), and tallies qualification rates. `run_tournament_simulation`
extends this through the entire knockout stage (official FIFA bracket via
bracket.py, round of 32 through the final and 3rd-place match), tallying each
team's probability of reaching every stage up to champion.

Kept separate from standings.py's expected-value projection
(project_group_table), which remains the default/cheap projection. Monte Carlo
is additive and opt-in.
"""

import random
from math import exp

from server.core import bracket, data, elo
from server.core import ratings_effective as reff
from server.core.config import MAX_GOALS, MONTE_CARLO_ITERATIONS, PENALTY_SKILL_WEIGHT


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


def _simulate_all_groups_once(
    fixture_params: dict[str, list[tuple]],
) -> tuple[dict[str, list[str]], list[dict]]:
    """Simulate one playthrough of all 12 groups.

    Returns (group_orders, ranked_thirds):
    - group_orders: {group: [1st, 2nd, 3rd, 4th]} per group.
    - ranked_thirds: the 12 third-placed teams ranked best-to-worst by
      (points, GD, GF), ties broken randomly, as
      [{"team", "group", "third_place_rank"}, ...].
    """
    group_orders = {}
    thirds = []
    for g, fx_params in fixture_params.items():
        order, table = _simulate_group_once(fx_params)
        group_orders[g] = order
        third_team = order[2]
        thirds.append((third_team, g, table[third_team]))

    random.shuffle(thirds)
    thirds.sort(key=lambda x: (x[2]["points"], x[2]["gf"] - x[2]["ga"], x[2]["gf"]), reverse=True)
    ranked_thirds = [
        {"team": team, "group": g, "third_place_rank": rank}
        for rank, (team, g, _) in enumerate(thirds, start=1)
    ]
    return group_orders, ranked_thirds


def run_simulation(iterations: int = MONTE_CARLO_ITERATIONS, seed: int | None = None) -> dict:
    """Run `iterations` full group-stage simulations and tally, per team:
    P(1st), P(2nd), P(3rd), P(4th), P(qualify via top-2), P(qualify via best
    third), and overall P(qualify) for the round of 32.
    """
    if seed is not None:
        random.seed(seed)

    teams = data.all_teams()
    fixture_params = _precompute_fixture_params()
    counts = {t: {"rank1": 0, "rank2": 0, "rank3": 0, "rank4": 0, "best_third": 0} for t in teams}

    for _ in range(iterations):
        group_orders, ranked_thirds = _simulate_all_groups_once(fixture_params)
        for order in group_orders.values():
            for rank, team in enumerate(order, start=1):
                counts[team][f"rank{rank}"] += 1
        for third in ranked_thirds[:8]:
            counts[third["team"]]["best_third"] += 1

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


def _knockout_winner(team_a: str, team_b: str) -> str:
    """Sample the winner of a single-elimination match: regulation result via
    Poisson scoreline; a draw goes to a penalty shootout, resolved with the
    same skill edge as elo.advance_probability (PENALTY_SKILL_WEIGHT).
    """
    rating_a = reff.effective_rating(team_a)
    rating_b = reff.effective_rating(team_b)
    advantage = reff.effective_advantage(team_a, team_b)

    score_a, score_b = _sample_score(rating_a, rating_b, advantage)
    if score_a != score_b:
        return team_a if score_a > score_b else team_b

    we = elo.win_expectancy(rating_a, rating_b, advantage)
    pen_a = 0.5 + (we - 0.5) * PENALTY_SKILL_WEIGHT
    return team_a if random.random() < pen_a else team_b


def run_tournament_simulation(iterations: int = MONTE_CARLO_ITERATIONS, seed: int | None = None) -> dict:
    """Run `iterations` full-tournament simulations (groups through the final)
    and tally, per team, the probability of reaching each stage: P(qualify
    for the round of 32), P(round of 16), P(quarterfinals), P(semifinals),
    P(final), P(champion), and P(third-place match).

    Every round follows the official FIFA bracket (bracket.py), resolved per
    iteration from the simulated group/round-of-32 results.
    """
    if seed is not None:
        random.seed(seed)

    teams = data.all_teams()
    fixture_params = _precompute_fixture_params()
    stages = ("rank1", "rank2", "best_third", "round_of_16", "quarterfinals",
              "semifinals", "final", "champion", "third_place_match")
    counts = {t: {s: 0 for s in stages} for t in teams}

    for _ in range(iterations):
        group_orders, ranked_thirds = _simulate_all_groups_once(fixture_params)
        for order in group_orders.values():
            for rank, team in enumerate(order[:2], start=1):
                counts[team][f"rank{rank}"] += 1
        qualified_thirds = ranked_thirds[:8]
        for third in qualified_thirds:
            counts[third["team"]]["best_third"] += 1

        groups_dict = {g: [{"team": t} for t in order] for g, order in group_orders.items()}
        fixtures = bracket.resolve_fixtures(groups_dict, qualified_thirds)

        r32_winners = {}
        for fx in fixtures:
            winner = _knockout_winner(fx["home"], fx["away"])
            r32_winners[fx["match"]] = winner
            counts[winner]["round_of_16"] += 1

        r16_winners = {}
        for fx, team_a, team_b in bracket.resolve_round(bracket.ROUND_OF_16, r32_winners):
            winner = _knockout_winner(team_a, team_b)
            r16_winners[fx["match"]] = winner
            counts[winner]["quarterfinals"] += 1

        qf_winners = {}
        for fx, team_a, team_b in bracket.resolve_round(bracket.QUARTERFINALS, r16_winners):
            winner = _knockout_winner(team_a, team_b)
            qf_winners[fx["match"]] = winner
            counts[winner]["semifinals"] += 1

        sf_winners = {}
        for fx, team_a, team_b in bracket.resolve_round(bracket.SEMIFINALS, qf_winners):
            winner = _knockout_winner(team_a, team_b)
            loser = team_b if winner == team_a else team_a
            sf_winners[fx["match"]] = winner
            counts[winner]["final"] += 1
            counts[loser]["third_place_match"] += 1

        _, final_a, final_b = bracket.resolve_round([bracket.FINAL], sf_winners)[0]
        champion = _knockout_winner(final_a, final_b)
        counts[champion]["champion"] += 1

    results = {}
    for t in teams:
        c = counts[t]
        results[t] = {
            "team": t,
            "group": data.group_of(t),
            "p_qualify": round((c["rank1"] + c["rank2"] + c["best_third"]) / iterations, 4),
            "p_round_of_16": round(c["round_of_16"] / iterations, 4),
            "p_quarterfinals": round(c["quarterfinals"] / iterations, 4),
            "p_semifinals": round(c["semifinals"] / iterations, 4),
            "p_final": round(c["final"] / iterations, 4),
            "p_champion": round(c["champion"] / iterations, 4),
            "p_third_place_match": round(c["third_place_match"] / iterations, 4),
        }
    return {"iterations": iterations, "teams": results}
