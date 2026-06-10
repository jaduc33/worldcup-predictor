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

# --- Recency-weighted form ----------------------------------------------------
FORM_WINDOW = _int("FORM_WINDOW", 4)                       # number of recent matches considered
FORM_WEIGHT = _float("FORM_WEIGHT", 8.0)                   # Elo points per unit of avg form score
FORM_MAX_ADJUSTMENT = _float("FORM_MAX_ADJUSTMENT", 40.0)  # cap on |form adjustment|, Elo points

# --- Host-nation advantage -------------------------------------------------------
HOST_ADV = _float("HOST_ADV", 60.0)  # Elo bump for USA/Canada/Mexico playing on home soil
                                      # (replaces manual rating edits; classic home-advantage size)

# --- Head-to-head blending ---------------------------------------------------------
H2H_WEIGHT = _float("H2H_WEIGHT", 0.15)        # blend share given to H2H-derived 1X2
H2H_MIN_MATCHES = _int("H2H_MIN_MATCHES", 3)   # minimum H2H meetings to apply any blend
H2H_MAX_MATCHES = _int("H2H_MAX_MATCHES", 10)  # cap on meetings considered
H2H_DECAY = _float("H2H_DECAY", 0.85)          # recency decay per meeting (most-recent-first)

# --- Monte Carlo group simulation ----------------------------------------------------
MONTE_CARLO_ITERATIONS = _int("MONTE_CARLO_ITERATIONS", 2000)  # 12 groups x 6 matches x N

# --- MCP server endpoint --------------------------------------------------------
MCP_HOST = os.environ.get("MCP_HOST", "127.0.0.1")
MCP_PORT = _int("MCP_PORT", 8000)
MCP_URL = os.environ.get("MCP_URL", f"http://{MCP_HOST}:{MCP_PORT}")
