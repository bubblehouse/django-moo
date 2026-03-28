# -*- coding: utf-8 -*-
"""
Tests for session-control verbs: PREFIX, SUFFIX, QUIET, OUTPUTPREFIX, OUTPUTSUFFIX.

These verbs set connection-level session settings via the Kombu message queue.
The set/clear tests verify the verb prints the correct confirmation message.
The show tests pre-populate _session_settings and verify display output.
"""

import pytest

from moo.core import code, parse
from moo.core.models import Object
from moo.shell.prompt import _session_settings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _set_registry(user_pk, key, value):
    """Directly populate the session settings registry for a test."""
    _session_settings.setdefault(user_pk, {})[key] = value


def _clear_registry(user_pk, *keys):
    """Remove test keys from the registry."""
    settings = _session_settings.get(user_pk, {})
    for key in keys:
        settings.pop(key, None)


# ---------------------------------------------------------------------------
# PREFIX
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_prefix_set(t_init: Object, t_wizard: Object):
    """PREFIX <marker> prints confirmation and stores the setting."""
    printed = []
    with pytest.warns(RuntimeWarning):
        with code.ContextManager(t_wizard, printed.append) as ctx:
            parse.interpret(ctx, "PREFIX >>START<<")
    assert any(">>START<<" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_prefix_clear(t_init: Object, t_wizard: Object):
    """PREFIX clear prints confirmation that the prefix was cleared."""
    printed = []
    with pytest.warns(RuntimeWarning):
        with code.ContextManager(t_wizard, printed.append) as ctx:
            parse.interpret(ctx, "PREFIX clear")
    assert any("cleared" in line.lower() for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_prefix_show_when_set(t_init: Object, t_wizard: Object):
    """PREFIX with no args shows the current prefix when one is set."""
    user_pk = t_wizard.owner.pk
    _set_registry(user_pk, "output_prefix", ">>START<<")
    try:
        printed = []
        with code.ContextManager(t_wizard, printed.append) as ctx:
            parse.interpret(ctx, "PREFIX")
        assert any(">>START<<" in line for line in printed)
    finally:
        _clear_registry(user_pk, "output_prefix")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_prefix_show_when_unset(t_init: Object, t_wizard: Object):
    """PREFIX with no args reports no prefix when none is set."""
    user_pk = t_wizard.owner.pk
    _clear_registry(user_pk, "output_prefix")
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "PREFIX")
    assert any("no" in line.lower() and "prefix" in line.lower() for line in printed)


# ---------------------------------------------------------------------------
# SUFFIX
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_suffix_set(t_init: Object, t_wizard: Object):
    """SUFFIX <marker> prints confirmation and stores the setting."""
    printed = []
    with pytest.warns(RuntimeWarning):
        with code.ContextManager(t_wizard, printed.append) as ctx:
            parse.interpret(ctx, "SUFFIX >>END<<")
    assert any(">>END<<" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_suffix_clear(t_init: Object, t_wizard: Object):
    """SUFFIX clear prints confirmation that the suffix was cleared."""
    printed = []
    with pytest.warns(RuntimeWarning):
        with code.ContextManager(t_wizard, printed.append) as ctx:
            parse.interpret(ctx, "SUFFIX clear")
    assert any("cleared" in line.lower() for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_suffix_show_when_set(t_init: Object, t_wizard: Object):
    """SUFFIX with no args shows the current suffix when one is set."""
    user_pk = t_wizard.owner.pk
    _set_registry(user_pk, "output_suffix", ">>END<<")
    try:
        printed = []
        with code.ContextManager(t_wizard, printed.append) as ctx:
            parse.interpret(ctx, "SUFFIX")
        assert any(">>END<<" in line for line in printed)
    finally:
        _clear_registry(user_pk, "output_suffix")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_suffix_show_when_unset(t_init: Object, t_wizard: Object):
    """SUFFIX with no args reports no suffix when none is set."""
    user_pk = t_wizard.owner.pk
    _clear_registry(user_pk, "output_suffix")
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "SUFFIX")
    assert any("no" in line.lower() and "suffix" in line.lower() for line in printed)


# ---------------------------------------------------------------------------
# QUIET
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_quiet_enable(t_init: Object, t_wizard: Object):
    """QUIET enable prints confirmation that quiet mode was enabled."""
    printed = []
    with pytest.warns(RuntimeWarning):
        with code.ContextManager(t_wizard, printed.append) as ctx:
            parse.interpret(ctx, "QUIET enable")
    assert any("enabled" in line.lower() for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_quiet_disable(t_init: Object, t_wizard: Object):
    """QUIET disable prints confirmation that quiet mode was disabled."""
    printed = []
    with pytest.warns(RuntimeWarning):
        with code.ContextManager(t_wizard, printed.append) as ctx:
            parse.interpret(ctx, "QUIET disable")
    assert any("disabled" in line.lower() for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_quiet_show_when_on(t_init: Object, t_wizard: Object):
    """QUIET with no args shows quiet mode is on when enabled."""
    user_pk = t_wizard.owner.pk
    _set_registry(user_pk, "quiet_mode", True)
    try:
        printed = []
        with code.ContextManager(t_wizard, printed.append) as ctx:
            parse.interpret(ctx, "QUIET")
        assert any("enabled" in line.lower() or "on" in line.lower() for line in printed)
    finally:
        _clear_registry(user_pk, "quiet_mode")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_quiet_show_when_off(t_init: Object, t_wizard: Object):
    """QUIET with no args shows quiet mode is off when not set."""
    user_pk = t_wizard.owner.pk
    _clear_registry(user_pk, "quiet_mode")
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "QUIET")
    assert any("disabled" in line.lower() or "off" in line.lower() for line in printed)


# ---------------------------------------------------------------------------
# OUTPUTPREFIX
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_outputprefix_set(t_init: Object, t_wizard: Object):
    """OUTPUTPREFIX <marker> prints confirmation and stores the setting."""
    printed = []
    with pytest.warns(RuntimeWarning):
        with code.ContextManager(t_wizard, printed.append) as ctx:
            parse.interpret(ctx, "OUTPUTPREFIX >>>")
    assert any(">>>" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_outputprefix_clear(t_init: Object, t_wizard: Object):
    """OUTPUTPREFIX clear prints confirmation that the global prefix was cleared."""
    printed = []
    with pytest.warns(RuntimeWarning):
        with code.ContextManager(t_wizard, printed.append) as ctx:
            parse.interpret(ctx, "OUTPUTPREFIX clear")
    assert any("cleared" in line.lower() for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_outputprefix_show_when_set(t_init: Object, t_wizard: Object):
    """OUTPUTPREFIX with no args shows the current global prefix when one is set."""
    user_pk = t_wizard.owner.pk
    _set_registry(user_pk, "output_global_prefix", ">>>")
    try:
        printed = []
        with code.ContextManager(t_wizard, printed.append) as ctx:
            parse.interpret(ctx, "OUTPUTPREFIX")
        assert any(">>>" in line for line in printed)
    finally:
        _clear_registry(user_pk, "output_global_prefix")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_outputprefix_show_when_unset(t_init: Object, t_wizard: Object):
    """OUTPUTPREFIX with no args reports no global prefix when none is set."""
    user_pk = t_wizard.owner.pk
    _clear_registry(user_pk, "output_global_prefix")
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "OUTPUTPREFIX")
    assert any("no" in line.lower() and "prefix" in line.lower() for line in printed)


# ---------------------------------------------------------------------------
# OUTPUTSUFFIX
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_outputsuffix_set(t_init: Object, t_wizard: Object):
    """OUTPUTSUFFIX <marker> prints confirmation and stores the setting."""
    printed = []
    with pytest.warns(RuntimeWarning):
        with code.ContextManager(t_wizard, printed.append) as ctx:
            parse.interpret(ctx, "OUTPUTSUFFIX <<<")
    assert any("<<<" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_outputsuffix_clear(t_init: Object, t_wizard: Object):
    """OUTPUTSUFFIX clear prints confirmation that the global suffix was cleared."""
    printed = []
    with pytest.warns(RuntimeWarning):
        with code.ContextManager(t_wizard, printed.append) as ctx:
            parse.interpret(ctx, "OUTPUTSUFFIX clear")
    assert any("cleared" in line.lower() for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_outputsuffix_show_when_set(t_init: Object, t_wizard: Object):
    """OUTPUTSUFFIX with no args shows the current global suffix when one is set."""
    user_pk = t_wizard.owner.pk
    _set_registry(user_pk, "output_global_suffix", "<<<")
    try:
        printed = []
        with code.ContextManager(t_wizard, printed.append) as ctx:
            parse.interpret(ctx, "OUTPUTSUFFIX")
        assert any("<<<" in line for line in printed)
    finally:
        _clear_registry(user_pk, "output_global_suffix")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_outputsuffix_show_when_unset(t_init: Object, t_wizard: Object):
    """OUTPUTSUFFIX with no args reports no global suffix when none is set."""
    user_pk = t_wizard.owner.pk
    _clear_registry(user_pk, "output_global_suffix")
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "OUTPUTSUFFIX")
    assert any("no" in line.lower() and "suffix" in line.lower() for line in printed)
