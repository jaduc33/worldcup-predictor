"""MCP tools: prediction tracking and scoring.

This is the layer that turns the project into something serious: every prediction
is logged, settled against the real result, and scored with the metrics actually
used for football forecasting -- chiefly the Ranked Probability Score (RPS), which
respects the ordering home_win > draw > away_win.
"""

import json
import math
from pathlib import Path

from server.core import elo
from server.core import ratings_effective as reff

STORE = Path(__file__).resolve().parents[2] / "data" / "predictions.json"
OUTCOMES = ("home_win", "draw", "away_win")


def _load() -> list:
    return json.loads(STORE.read_text(encoding="utf-8")) if STORE.exists() else []


def _save(records: list) -> None:
    STORE.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")


def _rps(probs: dict, outcome: str) -> float:
    """Ranked Probability Score for ordered 1X2 outcomes (lower = better)."""
    cum_p = cum_e = total = 0.0
    for o in OUTCOMES[:-1]:
        cum_p += probs[o]
        cum_e += 1.0 if o == outcome else 0.0
        total += (cum_p - cum_e) ** 2
    return total / (len(OUTCOMES) - 1)


def register(mcp):
    @mcp.tool
    def record_prediction(home: str, away: str) -> dict:
        """Compute a prediction (1X2 + exact score) and store it for later evaluation."""
        try:
            rating_home = reff.effective_rating(home)
            rating_away = reff.effective_rating(away)
        except KeyError as exc:
            return {"error": str(exc)}
        advantage = reff.effective_advantage(home, away)
        p = elo.match_probabilities(rating_home, rating_away, advantage=advantage)
        probs = {"home_win": p["win"], "draw": p["draw"], "away_win": p["loss"]}
        lambda_home, lambda_away = elo.expected_goals(rating_home, rating_away, advantage=advantage)
        exact_score = elo.expected_score(lambda_home, lambda_away)
        records = _load()
        records.append({
            "home": home, "away": away, "probs": probs,
            "exact_score": exact_score, "result": None, "actual_score": None,
        })
        _save(records)
        return {"stored": True, "index": len(records) - 1,
                "probabilities": {k: round(v, 3) for k, v in probs.items()},
                "exact_score": exact_score}

    @mcp.tool
    def record_result(home: str, away: str, outcome: str) -> dict:
        """Settle a stored prediction with the real outcome (home_win|draw|away_win)."""
        if outcome not in OUTCOMES:
            return {"error": f"outcome must be one of {OUTCOMES}"}
        records = _load()
        for rec in reversed(records):
            if rec["home"] == home and rec["away"] == away and rec["result"] is None:
                rec["result"] = outcome
                _save(records)
                return {"updated": True, "match": f"{home} v {away}", "outcome": outcome}
        return {"error": "no open prediction found for that match"}

    @mcp.tool
    def get_accuracy() -> dict:
        """Score all settled predictions (RPS, Brier, log-loss, 1X2 hit-rate, exact-score hit-rate)."""
        settled = [r for r in _load() if r["result"]]
        if not settled:
            return {"settled": 0, "message": "No settled predictions yet."}
        rps = brier = logloss = hits = 0.0
        exact_total = exact_hits = 0
        for rec in settled:
            p, outcome = rec["probs"], rec["result"]
            rps += _rps(p, outcome)
            brier += sum((p[k] - (1.0 if k == outcome else 0.0)) ** 2 for k in OUTCOMES)
            logloss += -math.log(max(p[outcome], 1e-12))
            hits += 1.0 if max(p, key=p.get) == outcome else 0.0
            if rec.get("exact_score") and rec.get("actual_score"):
                exact_total += 1
                exact_hits += 1.0 if rec["exact_score"] == rec["actual_score"] else 0.0
        n = len(settled)
        result = {
            "settled": n,
            "rps": round(rps / n, 4),
            "brier": round(brier / n, 4),
            "log_loss": round(logloss / n, 4),
            "hit_rate": round(hits / n, 3),
        }
        if exact_total:
            result["exact_score_evaluated"] = exact_total
            result["exact_score_hit_rate"] = round(exact_hits / exact_total, 3)
        return result
