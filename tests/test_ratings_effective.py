"""Tests for server/core/ratings_effective.py: effective rating/advantage helpers."""

import pytest

from server.core import data
from server.core import ratings_effective as reff
from server.core.config import HOST_ADV


def test_effective_rating_matches_base_rating_with_no_history():
    assert reff.effective_rating("France") == data.rating_of("France")


def test_effective_rating_unknown_team_raises_keyerror():
    with pytest.raises(KeyError):
        reff.effective_rating("Atlantis")


def test_host_bonus_for_host_nation():
    assert reff.host_bonus("USA") == HOST_ADV


def test_host_bonus_for_non_host_nation():
    assert reff.host_bonus("France") == 0.0


def test_effective_advantage_favors_host_when_home():
    assert reff.effective_advantage("Mexico", "South Korea") == pytest.approx(HOST_ADV)


def test_effective_advantage_favors_host_when_away():
    assert reff.effective_advantage("South Korea", "Mexico") == pytest.approx(-HOST_ADV)


def test_effective_advantage_is_zero_for_two_non_hosts():
    assert reff.effective_advantage("France", "Brazil") == pytest.approx(0.0)
