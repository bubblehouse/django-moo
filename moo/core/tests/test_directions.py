# -*- coding: utf-8 -*-
import pytest
from django.conf import settings


def test_directions_list_contains_all_cardinal():
    for d in ("north", "south", "east", "west", "up", "down"):
        assert d in settings.DIRECTIONS


def test_directions_list_contains_all_intercardinal():
    for d in ("northeast", "northwest", "southeast", "southwest"):
        assert d in settings.DIRECTIONS


def test_opposite_directions_round_trip():
    for d, opp in settings.OPPOSITE_DIRECTIONS.items():
        assert settings.OPPOSITE_DIRECTIONS[opp] == d, f"round-trip failed for {d!r}"


def test_sdk_exports_directions():
    from moo.sdk import DIRECTIONS, OPPOSITE_DIRECTIONS
    assert DIRECTIONS == settings.DIRECTIONS
    assert OPPOSITE_DIRECTIONS == settings.OPPOSITE_DIRECTIONS
