"""Tests for server/tools/knockout.py: knockout predictions and tournament simulation."""

import pytest
from fastmcp import FastMCP

from server.tools import knockout
from server.tools.knockout import _play_round, _predict_knockout, _simulate_round_of_32
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


def test_play_round_pairs_consecutive_teams():
    teams = ["France", "Brazil", "Spain", "Argentina"]
    matches, winners = _play_round(teams, "round_of_16")

    assert len(matches) == 2
    assert len(winners) == 2
    assert {matches[0]["team_a"], matches[0]["team_b"]} == {"France", "Brazil"}
    assert {matches[1]["team_a"], matches[1]["team_b"]} == {"Spain", "Argentina"}
    for m, w in zip(matches, winners):
        assert m["winner"] == w
        assert w in (m["team_a"], m["team_b"])
        assert m["loser"] in (m["team_a"], m["team_b"])
        assert m["loser"] != w


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
