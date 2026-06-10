"""MCP tools: 1X2 and exact-score predictions."""

from server.core import data, elo


def _predict(home: str, away: str) -> dict:
    rating_home, rating_away = data.rating_of(home), data.rating_of(away)

    p = elo.match_probabilities(rating_home, rating_away)
    probs = {
        "home_win": round(p["win"], 3),
        "draw": round(p["draw"], 3),
        "away_win": round(p["loss"], 3),
    }

    lambda_home, lambda_away = elo.expected_goals(rating_home, rating_away)
    top_scores = elo.most_likely_scores(lambda_home, lambda_away)

    return {
        "home": home,
        "away": away,
        "probabilities": probs,
        "pick": max(probs, key=probs.get),
        "exact_score": top_scores[0]["score"],
        "top_scores": top_scores,
    }


def register(mcp):
    @mcp.tool
    def predict_match(home: str, away: str) -> dict:
        """Predict 1X2 probabilities and the most likely exact scores for a match (neutral venue)."""
        try:
            return _predict(home, away)
        except KeyError as exc:
            return {"error": str(exc)}

    @mcp.tool
    def predict_group(group: str) -> dict:
        """Predict all 6 matches of a group at once (1X2 + exact-score predictions)."""
        g = group.upper()
        if g not in data.load_groups():
            return {"error": f"Unknown group '{group}'. Use A-L."}
        preds = [_predict(fx["home"], fx["away"]) for fx in data.group_fixtures(g)]
        return {"group": g, "predictions": preds}
