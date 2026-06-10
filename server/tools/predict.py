"""MCP tools: 1X2 and exact-score predictions."""

from server.core import data, elo, h2h
from server.core import football_api as api
from server.core import ratings_effective as reff


def _predict(home: str, away: str, use_h2h: bool = False) -> dict:
    rating_home = reff.effective_rating(home)
    rating_away = reff.effective_rating(away)
    advantage = reff.effective_advantage(home, away)

    p = elo.match_probabilities(rating_home, rating_away, advantage=advantage)

    h2h_applied = False
    if use_h2h:
        try:
            raw_sorted = sorted(api.head_to_head(home, away), key=lambda fx: fx["fixture"]["date"], reverse=True)
            simplified = [api.simplify_fixture(fx) for fx in raw_sorted]
            h2h_p = h2h.h2h_probabilities(simplified, team_a=home)
            if h2h_p is not None:
                p = h2h.blend_probabilities(p, h2h_p)
                h2h_applied = True
        except api.APIFootballError:
            pass  # graceful fallback to pure Elo -- no API key, quota, or fetch error

    probs = {
        "home_win": round(p["win"], 3),
        "draw": round(p["draw"], 3),
        "away_win": round(p["loss"], 3),
    }

    lambda_home, lambda_away = elo.expected_goals(rating_home, rating_away, advantage=advantage)
    top_scores = elo.most_likely_scores(lambda_home, lambda_away)

    return {
        "home": home,
        "away": away,
        "probabilities": probs,
        "pick": max(probs, key=probs.get),
        "exact_score": elo.expected_score(lambda_home, lambda_away),
        "top_scores": top_scores,
        "h2h_applied": h2h_applied,
    }


def register(mcp):
    @mcp.tool
    def predict_match(home: str, away: str, use_h2h: bool = False) -> dict:
        """Predict 1X2 probabilities and the most likely exact scores for a match.

        Set use_h2h=True to blend in historical head-to-head results (requires
        API_FOOTBALL_KEY; falls back silently to pure Elo if unavailable).
        """
        try:
            return _predict(home, away, use_h2h=use_h2h)
        except KeyError as exc:
            return {"error": str(exc)}

    @mcp.tool
    def predict_group(group: str) -> dict:
        """Predict all 6 matches of a group at once (1X2 + exact-score predictions).

        Does not use H2H -- 6 fixtures x 12 groups would exceed the
        API-Football free-tier quota.
        """
        g = group.upper()
        if g not in data.load_groups():
            return {"error": f"Unknown group '{group}'. Use A-L."}
        preds = [_predict(fx["home"], fx["away"]) for fx in data.group_fixtures(g)]
        return {"group": g, "predictions": preds}
