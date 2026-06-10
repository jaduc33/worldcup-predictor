"""MCP tools: group-stage projection and single-elimination knockout predictions."""

from server.core import bracket, data, elo, h2h, simulation, standings
from server.core import football_api as api
from server.core import ratings_effective as reff
from server.core.config import MONTE_CARLO_ITERATIONS


def _predict_knockout(team_a: str, team_b: str, use_h2h: bool = False) -> dict:
    rating_a = reff.effective_rating(team_a)
    rating_b = reff.effective_rating(team_b)
    advantage = reff.effective_advantage(team_a, team_b)

    p = elo.match_probabilities(rating_a, rating_b, advantage=advantage)

    h2h_applied = False
    if use_h2h:
        try:
            raw_sorted = sorted(api.head_to_head(team_a, team_b), key=lambda fx: fx["fixture"]["date"], reverse=True)
            simplified = [api.simplify_fixture(fx) for fx in raw_sorted]
            h2h_p = h2h.h2h_probabilities(simplified, team_a=team_a)
            if h2h_p is not None:
                p = h2h.blend_probabilities(p, h2h_p)
                h2h_applied = True
        except api.APIFootballError:
            pass  # graceful fallback to pure Elo -- no API key, quota, or fetch error

    probs_90min = {
        f"{team_a}_win": round(p["win"], 3),
        "draw": round(p["draw"], 3),
        f"{team_b}_win": round(p["loss"], 3),
    }

    lambda_a, lambda_b = elo.expected_goals(rating_a, rating_b, advantage=advantage)
    top_scores = elo.most_likely_scores(lambda_a, lambda_b)

    advance_a = elo.advance_probability(rating_a, rating_b, advantage=advantage)
    advance = {team_a: round(advance_a, 3), team_b: round(1 - advance_a, 3)}

    return {
        "team_a": team_a,
        "team_b": team_b,
        "probabilities_90min": probs_90min,
        "exact_score": elo.expected_score(lambda_a, lambda_b),
        "top_scores": top_scores,
        "advance_probability": advance,
        "favorite_to_advance": max(advance, key=advance.get),
        "h2h_applied": h2h_applied,
        "note": "Match nul après 90 min -> prolongation/tirs au but ; "
                "advance_probability inclut un léger avantage à l'équipe favorite aux tirs au but.",
    }


def _simulate_round_of_32() -> dict:
    projection = standings.project_all_groups()
    qualified_thirds = [r for r in projection["third_place_ranking"] if r["qualifies"]]
    fixtures = bracket.resolve_fixtures(projection["groups"], qualified_thirds)

    matches = []
    for fx in fixtures:
        prediction = _predict_knockout(fx["home"], fx["away"])
        matches.append({**fx, "prediction": prediction})

    return {
        "matches": matches,
        "qualified_round_of_16": [m["prediction"]["favorite_to_advance"] for m in matches],
        "note": standings.TIEBREAK_NOTE + " " + bracket.ASSIGNMENT_NOTE,
    }


def _play_round(teams: list[str], round_name: str) -> tuple[list[dict], list[str]]:
    """Pair up consecutive teams and predict each match. Returns (matches, winners)."""
    matches, winners = [], []
    for i in range(0, len(teams), 2):
        team_a, team_b = teams[i], teams[i + 1]
        prediction = _predict_knockout(team_a, team_b)
        winner = prediction["favorite_to_advance"]
        loser = team_b if winner == team_a else team_a
        matches.append({
            "round": round_name, "team_a": team_a, "team_b": team_b,
            "prediction": prediction, "winner": winner, "loser": loser,
        })
        winners.append(winner)
    return matches, winners


def register(mcp):
    @mcp.tool
    def simulate_group_stage(group: str) -> dict:
        """Project the final standings of a group from expected points/goals (not match-by-match)."""
        g = group.upper()
        if g not in data.load_groups():
            return {"error": f"Unknown group '{group}'. Use A-L."}
        table = standings.project_group_table(g)
        return {
            "group": g,
            "table": table,
            "qualified_top2": [table[0]["team"], table[1]["team"]],
            "third_place": table[2]["team"],
            "note": standings.TIEBREAK_NOTE,
        }

    @mcp.tool
    def simulate_all_groups() -> dict:
        """Project all 12 groups and rank the 12 third-placed teams to find the 8 that reach the round of 32."""
        result = standings.project_all_groups()
        qualified_thirds = [r for r in result["third_place_ranking"] if r["qualifies"]]
        eliminated_thirds = [r for r in result["third_place_ranking"] if not r["qualifies"]]
        return {
            "groups": result["groups"],
            "best_third_placed": qualified_thirds,
            "eliminated_third_placed": eliminated_thirds,
            "round_of_32_count": 24 + len(qualified_thirds),
            "note": standings.TIEBREAK_NOTE,
        }

    @mcp.tool
    def predict_knockout_match(team_a: str, team_b: str, use_h2h: bool = False) -> dict:
        """Predict a single-elimination match: 1X2 (90 min), exact score, and who advances.

        Set use_h2h=True to blend in historical head-to-head results (requires
        API_FOOTBALL_KEY; falls back silently to pure Elo if unavailable).
        """
        try:
            return _predict_knockout(team_a, team_b, use_h2h=use_h2h)
        except KeyError as exc:
            return {"error": str(exc)}

    @mcp.tool
    def simulate_groups_monte_carlo(iterations: int | None = None) -> dict:
        """Run a Monte Carlo simulation of all 12 group stages (default
        MONTE_CARLO_ITERATIONS iterations) and return per-team qualification
        probabilities: P(1st), P(2nd), P(3rd), P(4th), P(best third), P(qualify).

        Unlike simulate_all_groups (expected-value projection), this simulates
        each of the 6 group matches to a discrete result + scoreline per
        iteration, using the official points/GD/GF tiebreak order (ties beyond
        that broken randomly per iteration -- fair-play and the draw of lots
        aren't modelled).
        """
        n = iterations or MONTE_CARLO_ITERATIONS
        result = simulation.run_simulation(iterations=n)
        return {
            "iterations": result["iterations"],
            "teams": result["teams"],
            "note": "Egalite totale (points, diff. de buts, buts marques) departagee "
                    "aleatoirement a chaque iteration -- fair-play et tirage au sort "
                    "non modelises. " + standings.TIEBREAK_NOTE,
        }

    @mcp.tool
    def simulate_round_of_32() -> dict:
        """Project group-stage qualifiers and predict all 16 round-of-32 matches.

        Uses the official round-of-32 schedule (group-position formulas) with
        teams resolved from simulate_all_groups(); the 8 best-third slots are
        filled by a simplified heuristic (see the 'note' field).
        """
        return _simulate_round_of_32()

    @mcp.tool
    def simulate_tournament() -> dict:
        """Chain predictions from the round of 32 through to the final and 3rd-place match.

        The round of 32 uses the official bracket (group positions, see
        simulate_round_of_32). From the round of 16 onward, this uses a
        SIMPLIFIED SEQUENTIAL pairing (winners of consecutive round-of-32
        matches meet, then winners of consecutive round-of-16 matches, etc.)
        -- NOT the official FIFA bracket, which can only be resolved once the
        round-of-32 results are known.
        """
        r32 = _simulate_round_of_32()
        r32_winners = r32["qualified_round_of_16"]

        r16_matches, r16_winners = _play_round(r32_winners, "round_of_16")
        qf_matches, qf_winners = _play_round(r16_winners, "quarterfinals")
        sf_matches, sf_winners = _play_round(qf_winners, "semifinals")

        final_pred = _predict_knockout(sf_winners[0], sf_winners[1])
        champion = final_pred["favorite_to_advance"]
        runner_up = sf_winners[1] if champion == sf_winners[0] else sf_winners[0]

        sf_losers = [m["loser"] for m in sf_matches]
        third_pred = _predict_knockout(sf_losers[0], sf_losers[1])
        third_place = third_pred["favorite_to_advance"]
        fourth_place = sf_losers[1] if third_place == sf_losers[0] else sf_losers[0]

        return {
            "round_of_32": r32["matches"],
            "round_of_16": r16_matches,
            "quarterfinals": qf_matches,
            "semifinals": sf_matches,
            "third_place_match": {
                "team_a": sf_losers[0], "team_b": sf_losers[1],
                "prediction": third_pred, "winner": third_place,
            },
            "final": {
                "team_a": sf_winners[0], "team_b": sf_winners[1],
                "prediction": final_pred, "winner": champion,
            },
            "champion": champion,
            "runner_up": runner_up,
            "third_place": third_place,
            "fourth_place": fourth_place,
            "note": r32["note"] + " A partir des 8emes de finale, les confrontations suivent une "
                    "convention d'appariement SEQUENTIELLE simplifiee (vainqueurs de matchs "
                    "consecutifs s'affrontent) -- PAS le bracket officiel FIFA, qui depend des "
                    "resultats reels des 16es de finale.",
        }
