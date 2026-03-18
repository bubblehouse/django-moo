# pylint: disable=no-value-for-parameter  # Celery task decorator hides positional args from pylint
"""
Tests for exception classes in moo/core/exceptions.py.

Section 1: Pure unit tests verifying that each exception type produces a
           meaningful string message (no DB required).

Section 2: Integration tests confirming that naturally-triggered exceptions
           propagate through parse.interpret and are caught/formatted by
           tasks.parse_command.

Section 3: Integration tests for exceptions raised directly by core framework
           code: RecursiveError (Object.save), AmbiguousVerbError (Object.get_verb /
           parse_verb), and AccessError (Object.is_allowed).
"""

import pytest

from moo.core import code, exceptions, parse, tasks
from moo.sdk import create
from moo.core.models import Object
from moo.core.tests.utils import add_verb as _add_verb

# =============================================================================
# Section 1 — str() representation (no DB)
# =============================================================================


def test_user_error_str():
    """UserError.__str__ returns the message."""
    err = exceptions.UserError("something went wrong")
    assert str(err) == "something went wrong"


def test_usage_error_str():
    """UsageError.__str__ returns the usage message."""
    err = exceptions.UsageError("Usage: look at <object>")
    assert str(err) == "Usage: look at <object>"


def test_ambiguous_object_error_str():
    """AmbiguousObjectError.__str__ includes the name and both candidates."""
    err = exceptions.AmbiguousObjectError("coin", ["golden coin", "silver coin"])
    result = str(err)
    assert "coin" in result
    assert "golden coin" in result
    assert "silver coin" in result


def test_ambiguous_verb_error_str():
    """AmbiguousVerbError.__str__ includes the verb name and both candidates."""
    err = exceptions.AmbiguousVerbError("grab", ["chest", "bag"])
    result = str(err)
    assert "grab" in result
    assert "chest" in result
    assert "bag" in result


def test_access_error_str():
    """AccessError.__str__ identifies the accessor, action, and subject."""
    err = exceptions.AccessError("Alice", "read", "vault")
    result = str(err)
    assert "Alice" in result
    assert "read" in result
    assert "vault" in result


def test_recursive_error_str():
    """RecursiveError.__str__ returns the message."""
    err = exceptions.RecursiveError("Cannot put a container in itself")
    assert str(err) == "Cannot put a container in itself"


def test_quota_error_str():
    """QuotaError.__str__ returns the message."""
    err = exceptions.QuotaError("Object quota exceeded")
    assert str(err) == "Object quota exceeded"


def test_no_such_preposition_error_str():
    """NoSuchPrepositionError.__str__ returns the user-facing message."""
    err = exceptions.NoSuchPrepositionError("on")
    assert str(err) == "I don't understand you."


# =============================================================================
# Section 2 — Integration: natural triggers through parse.interpret /
#             tasks.parse_command
# =============================================================================


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_ambiguous_object_error_raised_by_parser(t_init, t_wizard):
    """Parser raises AmbiguousObjectError when two objects share a name in scope.

    The exception is raised inside Parser.__init__ while resolving the dobj,
    before any verb body even executes.
    """
    room = Object.objects.create(name="test room")
    room.add_verb("accept", code="return True")
    t_wizard.location = room
    t_wizard.save()
    loc = t_wizard.location
    create("coin", parents=[], location=loc)
    create("coin", parents=[], location=loc)

    # Verb body is irrelevant — the parser never reaches it.
    _add_verb(t_wizard, "grab", "pass", t_wizard)

    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        with pytest.raises(exceptions.AmbiguousObjectError) as exc_info:
            parse.interpret(ctx, "grab coin")

    assert "coin" in str(exc_info.value)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_ambiguous_object_error_caught_by_parse_command(t_init, t_wizard):
    """tasks.parse_command catches AmbiguousObjectError and formats it as bold red."""
    room = Object.objects.create(name="test room")
    room.add_verb("accept", code="return True")
    t_wizard.location = room
    t_wizard.save()
    loc = t_wizard.location
    create("coin", parents=[], location=loc)
    create("coin", parents=[], location=loc)
    _add_verb(t_wizard, "grab", "pass", t_wizard)

    result = tasks.parse_command(t_wizard.pk, "grab coin")

    assert any("[bold red]" in line for line in result)
    assert any("coin" in line for line in result)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_quota_error_raised_by_create(t_init, t_wizard):
    """QuotaError is raised by create() when the caller's quota is exhausted."""
    t_wizard.set_property("ownership_quota", 0)
    _add_verb(t_wizard, "test-quota", 'from moo.sdk import create; create("quota test object")', t_wizard)

    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        with pytest.raises(exceptions.QuotaError) as exc_info:
            parse.interpret(ctx, "test-quota")

    assert t_wizard.name in str(exc_info.value)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_quota_error_caught_by_parse_command(t_init, t_wizard):
    """tasks.parse_command catches QuotaError and formats it as bold red."""
    t_wizard.set_property("ownership_quota", 0)
    _add_verb(t_wizard, "test-quota", 'from moo.sdk import create; create("quota test object")', t_wizard)

    result = tasks.parse_command(t_wizard.pk, "test-quota")

    assert any("[bold red]" in line for line in result)
    assert any("quota" in line.lower() for line in result)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_no_such_preposition_error_raised_by_verb(t_init, t_wizard):
    """NoSuchPrepositionError is raised when verb code calls get_pobj_str() for
    a preposition that was not present in the command."""
    _add_verb(
        t_wizard,
        "test-prep",
        'from moo.sdk import context; context.parser.get_pobj_str("on")',
        t_wizard,
    )

    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        with pytest.raises(exceptions.NoSuchPrepositionError) as exc_info:
            parse.interpret(ctx, "test-prep")

    assert str(exc_info.value) == "I don't understand you."


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_no_such_preposition_error_caught_by_parse_command(t_init, t_wizard):
    """tasks.parse_command catches NoSuchPrepositionError and formats it as bold red."""
    _add_verb(
        t_wizard,
        "test-prep",
        'from moo.sdk import context; context.parser.get_pobj_str("on")',
        t_wizard,
    )

    result = tasks.parse_command(t_wizard.pk, "test-prep")

    assert any("[bold red]" in line for line in result)
    assert any("I don't understand you." in line for line in result)


# =============================================================================
# Section 3 — Core framework raises: RecursiveError, AmbiguousVerbError,
#             AccessError
# =============================================================================


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_recursive_error_raised_on_containment_loop(t_init, t_wizard):
    """RecursiveError is raised by Object.save() when moving an object would
    create a containment loop (box contains inner, then box.location = inner)."""
    with code.ContextManager(t_wizard, lambda _: None):
        box = create("box", parents=[])
        inner = create("inner box", parents=[])
        # Give box an accept verb so inner can move into it.
        _add_verb(box, "accept", "return True", t_wizard)
        inner.location = box
        inner.save()

        # Attempt to put box inside inner — would make box contain itself indirectly.
        # RecursiveError fires before the accept check for inner.
        box.location = inner
        with pytest.raises(exceptions.RecursiveError):
            box.save()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_ambiguous_verb_error_raised_by_get_verb(t_init, t_wizard):
    """AmbiguousVerbError is raised by Object.get_verb() when an object has
    multiple Verb rows with the same name defined directly on it."""
    with code.ContextManager(t_wizard, lambda _: None):
        obj = create("obj", parents=[])
        _add_verb(obj, "ambig-verb", "pass", t_wizard)
        _add_verb(obj, "ambig-verb", "pass", t_wizard)

        with pytest.raises(exceptions.AmbiguousVerbError) as exc_info:
            obj.get_verb("ambig-verb")

    assert "ambig-verb" in str(exc_info.value)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_access_error_raised_by_is_allowed(t_init, t_wizard):
    """AccessError is raised by is_allowed(fatal=True) when a deny rule fires.
    It must also be an instance of PermissionError (subclass)."""
    with code.ContextManager(t_wizard, lambda _: None):
        obj = create("secret", parents=[])
        stranger = Object.objects.create(name="stranger", owner=t_wizard)
        obj.deny(stranger, "read")

    with pytest.raises(exceptions.AccessError) as exc_info:
        stranger.is_allowed("read", obj, fatal=True)

    err = exc_info.value
    assert isinstance(err, PermissionError)
    assert "read" in str(err)
    assert "stranger" in str(err).lower() or str(stranger) in str(err)


# =============================================================================
# Section 4 — NoSuch*Error exceptions (replacing Django DoesNotExist)
#             through parse.interpret / tasks.parse_command
# =============================================================================


def test_no_such_object_error_is_user_error():
    """NoSuchObjectError is a UserError subclass and str() contains the name."""
    err = exceptions.NoSuchObjectError("ghost")
    assert isinstance(err, exceptions.UserError)
    assert "ghost" in str(err)


def test_no_such_verb_error_is_user_error():
    """NoSuchVerbError is a UserError subclass; .data stores the verb name."""
    err = exceptions.NoSuchVerbError("xyzzy")
    assert isinstance(err, exceptions.UserError)
    assert err.data == "xyzzy"


def test_no_such_property_error_is_user_error():
    """NoSuchPropertyError is a UserError subclass and str() contains the name."""
    err = exceptions.NoSuchPropertyError("color")
    assert isinstance(err, exceptions.UserError)
    assert "color" in str(err)


def test_no_such_property_error_with_origin():
    """NoSuchPropertyError with origin includes origin in str()."""
    err = exceptions.NoSuchPropertyError("color", origin="the lamp")
    assert "color" in str(err)
    assert "the lamp" in str(err)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_no_such_object_error_raised_by_get_dobj(t_init, t_wizard):
    """NoSuchObjectError is raised when verb code calls get_dobj()
    but no object by that name exists in scope."""
    _add_verb(
        t_wizard,
        "test-get-dobj",
        "from moo.sdk import context; context.parser.get_dobj()",
        t_wizard,
        direct_object="any",
    )
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        with pytest.raises(exceptions.NoSuchObjectError) as exc_info:
            parse.interpret(ctx, "test-get-dobj ghost")
    assert "ghost" in str(exc_info.value)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_no_such_object_error_caught_by_parse_command(t_init, t_wizard):
    """tasks.parse_command catches NoSuchObjectError and formats it as bold red."""
    _add_verb(
        t_wizard,
        "test-get-dobj",
        "from moo.sdk import context; context.parser.get_dobj()",
        t_wizard,
        direct_object="any",
    )
    result = tasks.parse_command(t_wizard.pk, "test-get-dobj ghost")
    assert any("[bold red]" in line for line in result)
    assert any("ghost" in line for line in result)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_no_such_verb_error_raised_by_parser(t_init, t_wizard):
    """NoSuchVerbError is raised by the parser when no object has a matching
    verb and the location has no huh verb to fall back to."""
    room = Object.objects.create(name="test room")
    room.add_verb("accept", code="return True")
    t_wizard.location = room
    t_wizard.save()
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        with pytest.raises(exceptions.NoSuchVerbError) as exc_info:
            parse.interpret(ctx, "xyzzy-no-such-verb")
    assert exc_info.value.data == "xyzzy-no-such-verb"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_no_such_verb_error_caught_by_parse_command(t_init, t_wizard):
    """tasks.parse_command catches NoSuchVerbError and formats it as bold red."""
    room = Object.objects.create(name="test room")
    room.add_verb("accept", code="return True")
    t_wizard.location = room
    t_wizard.save()
    result = tasks.parse_command(t_wizard.pk, "xyzzy-no-such-verb")
    assert any("[bold red]" in line for line in result)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_no_such_property_error_raised_by_get_property(t_init, t_wizard):
    """NoSuchPropertyError is raised when verb code calls get_property()
    for a property that does not exist on this or any ancestor."""
    _add_verb(
        t_wizard,
        "test-get-prop",
        'this.get_property("nonexistent_xyz_prop_qwerty")',
        t_wizard,
    )
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        with pytest.raises(exceptions.NoSuchPropertyError) as exc_info:
            parse.interpret(ctx, "test-get-prop")
    assert "nonexistent_xyz_prop_qwerty" in str(exc_info.value)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_no_such_property_error_caught_by_parse_command(t_init, t_wizard):
    """tasks.parse_command catches NoSuchPropertyError and formats it as bold red."""
    _add_verb(
        t_wizard,
        "test-get-prop",
        'this.get_property("nonexistent_xyz_prop_qwerty")',
        t_wizard,
    )
    result = tasks.parse_command(t_wizard.pk, "test-get-prop")
    assert any("[bold red]" in line for line in result)
