"""Round of 32 bracket structure for the 2026 World Cup (16 matches, 73-88).

Source: official tournament schedule -- group-position formulas per match
("1A" = Group A winner, "2B" = Group B runner-up, "3:M7" = the qualified
third-placed team assigned to the slot whose eligible groups are listed
under "M7" for match 7).

Rounds beyond the round of 32 (which winners meet in the round of 16, etc.)
are NOT modelled here: those pairings only become unambiguous once the
round-of-32 results are known.
"""

ROUND_OF_32 = [
    {"match": 1, "date": "2026-06-28", "venue": "SoFi Stadium, Los Angeles", "home": "2A", "away": "2B"},
    {"match": 2, "date": "2026-06-29", "venue": "NRG Stadium, Houston", "home": "1C", "away": "2F"},
    {"match": 3, "date": "2026-06-29", "venue": "Gillette Stadium, Boston", "home": "1E", "away": "3:M3"},
    {"match": 4, "date": "2026-06-29", "venue": "Estadio BBVA, Monterrey", "home": "1F", "away": "2C"},
    {"match": 5, "date": "2026-06-30", "venue": "AT&T Stadium, Dallas", "home": "2E", "away": "2I"},
    {"match": 6, "date": "2026-06-30", "venue": "MetLife Stadium, New York", "home": "1I", "away": "3:M6"},
    {"match": 7, "date": "2026-06-30", "venue": "Estadio Azteca, Mexico City", "home": "1A", "away": "3:M7"},
    {"match": 8, "date": "2026-07-01", "venue": "Mercedes-Benz Stadium, Atlanta", "home": "1L", "away": "3:M8"},
    {"match": 9, "date": "2026-07-01", "venue": "Lumen Field, Seattle", "home": "1G", "away": "3:M9"},
    {"match": 10, "date": "2026-07-01", "venue": "Levi's Stadium, Santa Clara", "home": "1D", "away": "3:M10"},
    {"match": 11, "date": "2026-07-02", "venue": "SoFi Stadium, Los Angeles", "home": "1H", "away": "2J"},
    {"match": 12, "date": "2026-07-02", "venue": "BMO Field, Toronto", "home": "2K", "away": "2L"},
    {"match": 13, "date": "2026-07-02", "venue": "BC Place, Vancouver", "home": "1B", "away": "3:M13"},
    {"match": 14, "date": "2026-07-03", "venue": "AT&T Stadium, Dallas", "home": "2D", "away": "2G"},
    {"match": 15, "date": "2026-07-03", "venue": "Hard Rock Stadium, Miami", "home": "1J", "away": "2H"},
    {"match": 16, "date": "2026-07-03", "venue": "Arrowhead Stadium, Kansas City", "home": "1K", "away": "3:M16"},
]

# For each "3:Mx" slot, the groups whose 3rd-placed team is eligible to fill it.
THIRD_PLACE_SLOTS = {
    "M3": {"A", "B", "C", "D", "F"},
    "M6": {"C", "D", "F", "G", "H"},
    "M7": {"C", "E", "F", "H", "I"},
    "M8": {"E", "H", "I", "J", "K"},
    "M9": {"A", "E", "H", "I", "J"},
    "M10": {"B", "E", "F", "I", "J"},
    "M13": {"E", "F", "G", "I", "J"},
    "M16": {"D", "E", "I", "J", "L"},
}

ASSIGNMENT_NOTE = (
    "Affectation des meilleurs 3emes aux 8 emplacements '3:Mx' par heuristique "
    "(emplacement le plus contraint d'abord, puis meilleur 3eme eligible) -- "
    "simplification du tableau officiel d'attribution FIFA, pas une garantie "
    "d'exactitude si plusieurs affectations valides existent."
)


def assign_third_placed(qualified_thirds: list[dict]) -> dict[str, dict]:
    """Assign the 8 qualified third-placed teams to the 8 '3:Mx' slots.

    Greedy most-constrained-slot-first: at each step, fill the slot with the
    fewest remaining eligible candidates, choosing its best-ranked candidate.
    """
    remaining = {r["group"]: r for r in qualified_thirds}
    slots = dict(THIRD_PLACE_SLOTS)
    assignment = {}
    while slots:
        slot, eligible = min(slots.items(), key=lambda kv: len(kv[1] & remaining.keys()))
        candidates = [g for g in eligible if g in remaining]
        if not candidates:
            raise ValueError(f"No eligible third-placed team left for slot {slot}")
        best = min(candidates, key=lambda g: remaining[g]["third_place_rank"])
        assignment[slot] = remaining.pop(best)
        del slots[slot]
    return assignment


def _resolve_spec(spec: str, groups: dict[str, list[dict]], third_assignment: dict[str, dict]) -> str:
    if spec.startswith("3:"):
        return third_assignment[spec[2:]]["team"]
    rank, group = int(spec[0]), spec[1]
    return groups[group][rank - 1]["team"]


def resolve_fixtures(groups: dict[str, list[dict]], qualified_thirds: list[dict]) -> list[dict]:
    """Resolve the 16 round-of-32 '1A'/'2B'/'3:Mx' specs into actual team names."""
    third_assignment = assign_third_placed(qualified_thirds)
    resolved = []
    for fx in ROUND_OF_32:
        resolved.append({
            "match": fx["match"],
            "date": fx["date"],
            "venue": fx["venue"],
            "home": _resolve_spec(fx["home"], groups, third_assignment),
            "away": _resolve_spec(fx["away"], groups, third_assignment),
            "home_spec": fx["home"],
            "away_spec": fx["away"],
        })
    return resolved
