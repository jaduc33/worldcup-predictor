"""Group-stage table projection: expected points/goals from the prediction model.

Like elo.py, this is intentionally simple: instead of simulating each of the 6
group matches to a single result, every match contributes its EXPECTED points
and goals to both teams. Ranking then mirrors the official tiebreak order
(points -> goal difference -> goals scored). Fair-play points and the final
drawing of lots aren't modelled.
"""

from server.core import data, elo
from server.core import ratings_effective as reff

TIEBREAK_NOTE = (
    "Classement basé sur points/buts ATTENDUS (issus du modèle), pas une "
    "simulation match par match. Ordre des critères officiels : points, "
    "différence de buts, buts marqués. Fair-play et tirage au sort ne sont "
    "pas modélisables."
)


def project_group_table(group: str) -> list[dict]:
    """Return the 4 teams of `group`, ranked by expected points/GD/GF (rank 1-4)."""
    teams = data.load_groups()[group]
    stats = {t: {"exp_points": 0.0, "exp_gf": 0.0, "exp_ga": 0.0} for t in teams}

    for fx in data.group_fixtures(group):
        home, away = fx["home"], fx["away"]
        rh, ra = reff.effective_rating(home), reff.effective_rating(away)
        advantage = reff.effective_advantage(home, away)
        p = elo.match_probabilities(rh, ra, advantage=advantage)
        lh, la = elo.expected_goals(rh, ra, advantage=advantage)

        stats[home]["exp_points"] += 3 * p["win"] + p["draw"]
        stats[away]["exp_points"] += 3 * p["loss"] + p["draw"]
        stats[home]["exp_gf"] += lh
        stats[home]["exp_ga"] += la
        stats[away]["exp_gf"] += la
        stats[away]["exp_ga"] += lh

    table = []
    for t in teams:
        s = stats[t]
        table.append({
            "team": t,
            "exp_points": round(s["exp_points"], 2),
            "exp_gf": round(s["exp_gf"], 2),
            "exp_ga": round(s["exp_ga"], 2),
            "exp_gd": round(s["exp_gf"] - s["exp_ga"], 2),
        })

    table.sort(key=lambda r: (r["exp_points"], r["exp_gd"], r["exp_gf"]), reverse=True)
    for i, row in enumerate(table, start=1):
        row["rank"] = i
    return table


def rank_third_placed(tables: dict[str, list[dict]]) -> list[dict]:
    """Rank the 12 third-placed teams across groups using the same criteria."""
    thirds = []
    for g, table in tables.items():
        row = dict(table[2])
        row["group"] = g
        thirds.append(row)
    thirds.sort(key=lambda r: (r["exp_points"], r["exp_gd"], r["exp_gf"]), reverse=True)
    for i, row in enumerate(thirds, start=1):
        row["third_place_rank"] = i
        row["qualifies"] = i <= 8
    return thirds


def project_all_groups() -> dict:
    """Project all 12 group tables and rank the third-placed teams."""
    tables = {g: project_group_table(g) for g in data.load_groups()}
    return {"groups": tables, "third_place_ranking": rank_third_placed(tables)}
