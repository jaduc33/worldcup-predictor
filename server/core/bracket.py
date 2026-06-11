"""Knockout bracket structure for the 2026 World Cup (matches 73-104), per the
official FIFA bracket.

Round of 32 (matches 73-88, "match" 1-16 below): group-position formulas per
match ("1A" = Group A winner, "2B" = Group B runner-up, "3:M7" = the qualified
third-placed team assigned to the slot whose eligible groups are listed under
"M7" for match 7).

Round of 16 onward (ROUND_OF_16, QUARTERFINALS, SEMIFINALS, FINAL,
THIRD_PLACE): unlike the group-position formulas above, WHICH WINNERS MEET is
fixed in advance by the official bracket and does not depend on the actual
round-of-32 results -- only the team names filling each slot do. Each entry's
"home"/"away" reference the "match" number of the corresponding fixture in the
previous round (e.g. round-of-16 match 89 is between the winners of
round-of-32 matches 3 and 6); resolve_round() looks those up.
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

# Round of 16 (matches 89-96): "home"/"away" reference round-of-32 "match" numbers.
ROUND_OF_16 = [
    {"match": 89, "date": "2026-07-04", "home": 3, "away": 6},
    {"match": 90, "date": "2026-07-04", "home": 1, "away": 4},
    {"match": 91, "date": "2026-07-05", "home": 2, "away": 5},
    {"match": 92, "date": "2026-07-06", "home": 7, "away": 8},
    {"match": 93, "date": "2026-07-06", "home": 12, "away": 11},
    {"match": 94, "date": "2026-07-07", "home": 10, "away": 9},
    {"match": 95, "date": "2026-07-07", "home": 14, "away": 15},
    {"match": 96, "date": "2026-07-07", "home": 13, "away": 16},
]

# Quarterfinals (matches 97-100): "home"/"away" reference round-of-16 "match" numbers.
QUARTERFINALS = [
    {"match": 97, "date": "2026-07-09", "home": 89, "away": 90},
    {"match": 98, "date": "2026-07-10", "home": 93, "away": 94},
    {"match": 99, "date": "2026-07-11", "home": 91, "away": 92},
    {"match": 100, "date": "2026-07-12", "home": 95, "away": 96},
]

# Semifinals (matches 101-102): "home"/"away" reference quarterfinal "match" numbers.
SEMIFINALS = [
    {"match": 101, "date": "2026-07-14", "home": 97, "away": 98},
    {"match": 102, "date": "2026-07-15", "home": 99, "away": 100},
]

# Final (match 104) and 3rd-place match (match 103): "home"/"away" reference
# semifinal "match" numbers. The 3rd-place match is between the two losers.
FINAL = {"match": 104, "date": "2026-07-19", "home": 101, "away": 102}
THIRD_PLACE = {"match": 103, "date": "2026-07-18", "home": 101, "away": 102}


def resolve_round(schedule: list[dict], prev_results: dict[int, str]) -> list[tuple[dict, str, str]]:
    """For each entry in `schedule`, resolve its "home"/"away" match-number
    references against `prev_results` (previous round's "match" number ->
    team that emerged from it -- a winner, or for THIRD_PLACE, a loser).

    Returns a list of (schedule_entry, team_a, team_b) tuples.
    """
    return [(fx, prev_results[fx["home"]], prev_results[fx["away"]]) for fx in schedule]


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

    Backtracking search over THIRD_PLACE_SLOTS: for each slot (in fixed order),
    try its remaining eligible candidates best-ranked first, backtracking
    whenever a choice leaves a later slot with no eligible team. With 8 slots
    and at most 8 candidates this is exhaustive but cheap, and -- unlike a
    single greedy pass -- always finds a valid assignment if one exists.
    """
    by_group = {r["group"]: r for r in qualified_thirds}
    slot_names = list(THIRD_PLACE_SLOTS)

    def backtrack(i: int, remaining: set[str], assignment: dict[str, dict]) -> dict[str, dict] | None:
        if i == len(slot_names):
            return assignment
        slot = slot_names[i]
        candidates = sorted(
            (g for g in THIRD_PLACE_SLOTS[slot] if g in remaining),
            key=lambda g: by_group[g]["third_place_rank"],
        )
        for g in candidates:
            assignment[slot] = by_group[g]
            result = backtrack(i + 1, remaining - {g}, assignment)
            if result is not None:
                return result
            del assignment[slot]
        return None

    result = backtrack(0, set(by_group), {})
    if result is None:
        raise ValueError("No valid assignment of third-placed teams to bracket slots")
    return result


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
