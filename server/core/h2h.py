"""Head-to-head probability blending: fold historical W/D/L rates between two
teams into the Elo-derived 1X2 probabilities. Pure functions over a list of
simplified H2H records (see football_api.simplify_fixture) -- no network calls
here; the caller fetches via football_api and handles APIFootballError.
"""

from server.core.config import H2H_DECAY, H2H_MAX_MATCHES, H2H_MIN_MATCHES, H2H_WEIGHT


def h2h_probabilities(matches: list[dict], team_a: str) -> dict | None:
    """Compute recency-weighted W/D/L rates for `team_a` from up to
    H2H_MAX_MATCHES most-recent H2H `matches` (each a simplified fixture dict
    with "home", "away", "score" = "X-Y", most-recent first).

    Returns None if fewer than H2H_MIN_MATCHES usable matches are available
    (caller falls back to pure Elo).
    """
    usable = [m for m in matches if m.get("score")][:H2H_MAX_MATCHES]
    if len(usable) < H2H_MIN_MATCHES:
        return None

    w = d = l = 0.0
    total_weight = 0.0
    for i, m in enumerate(usable):
        weight = H2H_DECAY ** i
        gh, ga = (int(x) for x in m["score"].split("-"))
        goals_for = gh if m["home"] == team_a else ga
        goals_against = ga if m["home"] == team_a else gh

        if goals_for > goals_against:
            w += weight
        elif goals_for == goals_against:
            d += weight
        else:
            l += weight
        total_weight += weight

    return {"win": w / total_weight, "draw": d / total_weight, "loss": l / total_weight}


def blend_probabilities(elo_probs: dict, h2h_probs: dict | None, weight: float = H2H_WEIGHT) -> dict:
    """Blend Elo-derived `elo_probs` with `h2h_probs` (or return elo_probs
    unchanged if h2h_probs is None). `weight` is the H2H share of the blend.
    """
    if h2h_probs is None:
        return elo_probs

    blended = {
        k: (1 - weight) * elo_probs[k] + weight * h2h_probs[k]
        for k in ("win", "draw", "loss")
    }
    total = sum(blended.values())
    return {k: v / total for k, v in blended.items()}
