"""Centralized configuration: tunable model parameters and the MCP endpoint.

Every value below can be overridden via environment variables (loaded from
.env by server/app.py), so the prediction model can be recalibrated --
see server/tools/evaluate.get_accuracy -- without touching code.
"""

import os


def _float(name: str, default: float) -> float:
    return float(os.environ.get(name, default))


def _int(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


# --- 1X2 model ---------------------------------------------------------------
DRAW_BASE = _float("DRAW_BASE", 0.30)  # draw probability when two teams are perfectly even
HOME_ADV = _float("HOME_ADV", 0.0)     # neutral venues at a World Cup; give a host nation a
                                        # bump by editing its rating instead, or via this.
K_FACTOR = _float("K_FACTOR", 40)      # Elo update magnitude for World Cup matches

# --- Exact-score goal model ---------------------------------------------------
AVG_GOALS = _float("AVG_GOALS", 1.25)                  # expected goals/side, even matchup (total ~2.5)
GOAL_RATING_SCALE = _float("GOAL_RATING_SCALE", 400)   # Elo points needed to double expected goals
MAX_GOALS = _int("MAX_GOALS", 6)                       # scoreline grid bound (0..N each side)

# --- Knockout model ------------------------------------------------------------
PENALTY_SKILL_WEIGHT = _float("PENALTY_SKILL_WEIGHT", 0.2)  # skill influence on penalty shootouts

# --- MCP server endpoint --------------------------------------------------------
MCP_HOST = os.environ.get("MCP_HOST", "127.0.0.1")
MCP_PORT = _int("MCP_PORT", 8000)
MCP_URL = os.environ.get("MCP_URL", f"http://{MCP_HOST}:{MCP_PORT}")
