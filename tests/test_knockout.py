"""Tests for server/tools/knockout.py: knockout predictions and tournament simulation."""

import pytest
from fastmcp import FastMCP

from server.core import bracket
from server.tools import knockout
from server.tools.knockout import _predict_knockout, _simulate_round_of_32
from tests._helpers import call_tool


def test_predict_knockout_advance_probabilities_sum_to_one():
    result = _predict_knockout("France", "Brazil")
    advance = result["advance_probability"]
    assert sum(advance.values()) == pytest.approx(1.0)


def test_predict_knockout_favorite_matches_higher_advance_probability():
    result = _predict_knockout("France", "Brazil")
    advance = result["advance_probability"]
    assert result["favorite_to_advance"] == max(advance, key=advance.get)


def test_predict_knockout_stronger_team_more_likely_to_advance():
    result = _predict_knockout("Spain", "Curacao")
    assert result["advance_probability"]["Spain"] > 0.5
    assert result["favorite_to_advance"] == "Spain"


def test_simulate_round_of_32_produces_16_matches_and_winners():
    result = _simulate_round_of_32()
    assert len(result["matches"]) == 16
    assert len(result["qualified_round_of_16"]) == 16

    teams = {m["home"] for m in result["matches"]} | {m["away"] for m in result["matches"]}
    assert len(teams) == 32


@pytest.fixture
def mcp_app():
    mcp = FastMCP("test")
    knockout.register(mcp)
    return mcp


def test_simulate_tournament_produces_a_full_bracket(mcp_app):
    result = call_tool(mcp_app, "simulate_tournament")

    assert len(result["round_of_32"]) == 16
    assert len(result["round_of_16"]) == 8
    assert len(result["quarterfinals"]) == 4
    assert len(result["semifinals"]) == 2

    podium = {result["champion"], result["runner_up"], result["third_place"], result["fourth_place"]}
    assert len(podium) == 4


def test_simulate_tournament_follows_official_bracket_pairings(mcp_app):
    """Each round's matches must follow the fixed FIFA pairing in bracket.py,
    not an arbitrary/sequential order."""
    result = call_tool(mcp_app, "simulate_tournament")

    r32_winners = {m["match"]: m["prediction"]["favorite_to_advance"] for m in result["round_of_32"]}
    for fx, expected_a, expected_b in bracket.resolve_round(bracket.ROUND_OF_16, r32_winners):
        m = next(x for x in result["round_of_16"] if x["match"] == fx["match"])
        assert {m["home"], m["away"]} == {expected_a, expected_b}

    r16_winners = {m["match"]: m["winner"] for m in result["round_of_16"]}
    for fx, expected_a, expected_b in bracket.resolve_round(bracket.QUARTERFINALS, r16_winners):
        m = next(x for x in result["quarterfinals"] if x["match"] == fx["match"])
        assert {m["home"], m["away"]} == {expected_a, expected_b}

    qf_winners = {m["match"]: m["winner"] for m in result["quarterfinals"]}
    for fx, expected_a, expected_b in bracket.resolve_round(bracket.SEMIFINALS, qf_winners):
        m = next(x for x in result["semifinals"] if x["match"] == fx["match"])
        assert {m["home"], m["away"]} == {expected_a, expected_b}

    sf_winners = {m["match"]: m["winner"] for m in result["semifinals"]}
    sf_losers = {m["match"]: m["loser"] for m in result["semifinals"]}

    _, final_a, final_b = bracket.resolve_round([bracket.FINAL], sf_winners)[0]
    assert {result["final"]["home"], result["final"]["away"]} == {final_a, final_b}

    _, third_a, third_b = bracket.resolve_round([bracket.THIRD_PLACE], sf_losers)[0]
    assert {result["third_place_match"]["home"], result["third_place_match"]["away"]} == {third_a, third_b}


def test_simulate_tournament_monte_carlo_returns_per_team_probabilities(mcp_app):
    result = call_tool(mcp_app, "simulate_tournament_monte_carlo", {"iterations": 50})

    assert result["iterations"] == 50

    teams = result["teams"]
    assert len(teams) == 48

    for team_result in teams.values():
        for key in ("p_qualify", "p_round_of_16", "p_quarterfinals",
                     "p_semifinals", "p_final", "p_champion", "p_third_place_match"):
            assert 0.0 <= team_result[key] <= 1.0
