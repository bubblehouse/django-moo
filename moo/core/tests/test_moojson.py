# -*- coding: utf-8 -*-
"""
Tests for moo/core/moojson.py — JSON encoding/decoding of MOO types.
"""

from datetime import date, datetime, time, timezone

import pytest

from .. import moojson

# ---------------------------------------------------------------------------
# datetime
# ---------------------------------------------------------------------------


def test_datetime_roundtrip_with_timezone():
    dt = datetime(2025, 6, 15, 12, 30, 45, tzinfo=timezone.utc)
    assert moojson.loads(moojson.dumps(dt)) == dt


def test_datetime_roundtrip_naive():
    dt = datetime(2025, 6, 15, 12, 30, 45)
    assert moojson.loads(moojson.dumps(dt)) == dt


def test_datetime_encodes_as_dt_prefix():
    import json

    dt = datetime(2025, 1, 1, tzinfo=timezone.utc)
    raw = json.loads(moojson.dumps(dt))
    assert "dt#" in raw
    assert raw["dt#"] == dt.isoformat()


# ---------------------------------------------------------------------------
# date
# ---------------------------------------------------------------------------


def test_date_roundtrip():
    d = date(2025, 6, 15)
    assert moojson.loads(moojson.dumps(d)) == d


def test_date_encodes_as_d_prefix():
    import json

    d = date(2025, 6, 15)
    raw = json.loads(moojson.dumps(d))
    assert "d#" in raw
    assert raw["d#"] == d.isoformat()


def test_date_does_not_encode_as_datetime():
    import json

    d = date(2025, 6, 15)
    raw = json.loads(moojson.dumps(d))
    assert "dt#" not in raw


# ---------------------------------------------------------------------------
# time
# ---------------------------------------------------------------------------


def test_time_roundtrip():
    t = time(14, 30, 59)
    assert moojson.loads(moojson.dumps(t)) == t


def test_time_roundtrip_with_timezone():
    t = time(14, 30, 59, tzinfo=timezone.utc)
    assert moojson.loads(moojson.dumps(t)) == t


def test_time_encodes_as_t_prefix():
    import json

    t = time(8, 0, 0)
    raw = json.loads(moojson.dumps(t))
    assert "t#" in raw
    assert raw["t#"] == t.isoformat()


# ---------------------------------------------------------------------------
# Nested structures
# ---------------------------------------------------------------------------


def test_datetime_in_list():
    dt = datetime(2025, 3, 12, tzinfo=timezone.utc)
    result = moojson.loads(moojson.dumps([dt, "hello", 42]))
    assert result == [dt, "hello", 42]


def test_datetime_in_dict_value():
    dt = datetime(2025, 3, 12, tzinfo=timezone.utc)
    # dicts with more than one key pass through unchanged, so wrap value in list
    result = moojson.loads(moojson.dumps({"ts": [dt]}))
    assert result == {"ts": [dt]}


def test_mixed_date_types_in_list():
    dt = datetime(2025, 6, 15, 12, 0, tzinfo=timezone.utc)
    d = date(2025, 6, 15)
    t = time(12, 0, 0)
    result = moojson.loads(moojson.dumps([dt, d, t]))
    assert result == [dt, d, t]


# ---------------------------------------------------------------------------
# Pass-through — unknown single-key dicts are returned as-is
# ---------------------------------------------------------------------------


def test_unknown_single_key_dict_passthrough():
    import json

    payload = json.dumps({"x#": "something"})
    result = moojson.loads(payload)
    assert result == {"x#": "something"}


def test_multi_key_dict_passthrough():
    import json

    payload = json.dumps({"dt#": "2025-01-01", "extra": "field"})
    result = moojson.loads(payload)
    assert result == {"dt#": "2025-01-01", "extra": "field"}


# ---------------------------------------------------------------------------
# DB-backed: Object, Verb, Property round-trips
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_roundtrip(t_init, t_wizard):
    from .. import code, create

    with code.ContextManager(t_wizard, lambda m: None):
        obj = create("moojson test object")
    result = moojson.loads(moojson.dumps(obj))
    assert result.pk == obj.pk


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_verb_roundtrip(t_init, t_wizard):
    from .. import code, create

    with code.ContextManager(t_wizard, lambda m: None):
        obj = create("moojson verb object")
        obj.add_verb("test_verb", code="pass")
    verb = obj.verbs.get(names__name="test_verb")
    result = moojson.loads(moojson.dumps(verb))
    assert result.pk == verb.pk


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_property_roundtrip(t_init, t_wizard):
    from .. import code, create
    from ..models import Property

    with code.ContextManager(t_wizard, lambda m: None):
        obj = create("moojson prop object")
        obj.set_property("test_prop", "value")
    prop = obj.properties.get(name="test_prop")
    result = moojson.loads(moojson.dumps(prop))
    assert result.pk == prop.pk


# ---------------------------------------------------------------------------
# dumps raises TypeError for unserializable types
# ---------------------------------------------------------------------------


def test_dumps_raises_for_unknown_type():
    with pytest.raises(TypeError):
        moojson.dumps(object())
