"""Effective rating/advantage helpers: combine the static Elo rating with the
recency-form adjustment (form.py) and the structured host-nation advantage
(config.HOST_ADV), so all prediction call sites apply both consistently.
"""

from server.core import data, form
from server.core.config import HOST_ADV


def effective_rating(team: str) -> float:
    """Elo rating + form adjustment (0.0 if no/insufficient match history)."""
    return data.rating_of(team) + form.team_form_adjustment(team)


def host_bonus(team: str) -> float:
    """HOST_ADV if `team` is one of the World Cup hosts, else 0.0."""
    return HOST_ADV if team in data.load_hosts() else 0.0


def effective_advantage(home: str, away: str, base_advantage: float = 0.0) -> float:
    """Return the advantage term to pass to elo.match_probabilities/expected_goals
    for a `home` vs `away` matchup: base_advantage (e.g. HOME_ADV) plus a host
    bonus for whichever side is a host nation. The "home"/"away" labels in
    group_fixtures() are arbitrary fixture-data labels, not real venue
    assignments -- this stays sign-correct either way: if `away` is the host,
    its bonus correctly reduces the home side's advantage term.
    """
    return base_advantage + host_bonus(home) - host_bonus(away)
