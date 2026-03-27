# -*- coding: utf-8 -*-
# pylint: disable=protected-access
"""
Security tests: import blocking and allowed-module return-value surfaces.

Covers: ContextManager, _publish_to_player, string module,
moo.core submodules, SDK internal names, module attribute traversal,
django_celery_beat import block, and re/hashlib/datetime/time return objects.
"""

from .utils import mock_caller, raises_in_verb

# ---------------------------------------------------------------------------
# ContextManager must not be importable via moo.sdk
# ---------------------------------------------------------------------------


def test_context_manager_not_importable():
    """

    ContextManager is in BLOCKED_IMPORTS for moo.sdk.
    Verb code must not be able to call override_caller() to impersonate another player.
    """
    raises_in_verb("from moo.sdk import ContextManager", ImportError)


# ---------------------------------------------------------------------------
# _publish_to_player must not be importable via moo.sdk
# ---------------------------------------------------------------------------


def test_publish_to_player_not_importable():
    """

    _publish_to_player must not be accessible from verb code.
    RestrictedPython rejects _-prefixed names at compile time (TypeError on exec),
    and BLOCKED_IMPORTS provides defense-in-depth at the import level.
    """
    raises_in_verb("from moo.sdk import _publish_to_player", (ImportError, TypeError))


# ---------------------------------------------------------------------------
# string module must not be importable
# ---------------------------------------------------------------------------


def test_string_module_not_importable():
    """

    'string' was removed from ALLOWED_MODULES because string.Formatter.get_field
    calls CPython's real getattr internally, bypassing safe_getattr and allowing
    dunder attribute access (e.g. __class__) to reach the Django ORM.
    """
    raises_in_verb("import string", ImportError)


# ---------------------------------------------------------------------------
# moo.sdk must not expose internal framework names
# ---------------------------------------------------------------------------


def test_models_not_in_sdk():
    """

    `from moo.sdk import models` must raise ImportError.
    Django ORM model classes (Object.objects, User.objects, etc.) must not be
    reachable from verb code via the public SDK.
    """
    raises_in_verb("from moo.sdk import models", ImportError)


def test_auth_not_in_sdk():
    """

    `from moo.sdk import auth` must raise ImportError.
    auth re-exports Player and User ORM models and must not be verb-accessible.
    """
    raises_in_verb("from moo.sdk import auth", ImportError)


def test_tasks_not_in_sdk():
    """

    `from moo.sdk import tasks` must raise ImportError.
    tasks exposes raw Celery task functions that bypass the invoke() permission guards.
    """
    raises_in_verb("from moo.sdk import tasks", ImportError)


def test_code_not_in_sdk():
    """

    `from moo.sdk import code` must raise ImportError.
    code exposes ContextManager, providing an indirect path to override_caller()
    even though ContextManager itself is blocked by name.
    """
    raises_in_verb("from moo.sdk import code", ImportError)


# ---------------------------------------------------------------------------
# moo.sdk module attribute access must not expose blocked names (pass 7)
# ---------------------------------------------------------------------------


def test_sdk_contextmanager_blocked_via_module_attribute():
    """

    ContextManager is imported as _ContextManager (underscore alias) in moo/sdk.py.
    Accessing it as `sdk.ContextManager` is blocked because BLOCKED_IMPORTS contains
    'ContextManager' for 'moo.sdk', and the ModuleType guard in get_protected_attribute
    enforces BLOCKED_IMPORTS for attribute-access paths too.
    """
    raises_in_verb(
        "import moo.sdk as sdk\nx = sdk.ContextManager",
        AttributeError,
    )


def test_sdk_module_traversal_to_core_blocked():
    """

    `import moo.sdk` (bare, no 'as') binds the top-level `moo` package.
    The ModuleType guard in get_protected_attribute blocks attribute access to any
    submodule whose name is not in ALLOWED_MODULES/WIZARD_ALLOWED_MODULES, so
    `moo.core` raises AttributeError before the ORM is reachable.
    """
    raises_in_verb(
        "import moo.sdk\nx = moo.core",
        AttributeError,
    )


# ---------------------------------------------------------------------------
# moo.sdk must not expose non-public framework helpers (pass 15)
# ---------------------------------------------------------------------------


def test_sdk_contextmanager_function_blocked():
    """

    `contextmanager` is imported at module level in moo/sdk.py from contextlib.
    It is not in __all__ and has no verb-code use case.  BLOCKED_IMPORTS for
    moo.sdk now includes 'contextmanager' to prevent verb code from accessing it
    via `from moo.sdk import contextmanager` or `import moo.sdk as sdk; sdk.contextmanager`.
    """
    raises_in_verb(
        "from moo.sdk import contextmanager",
        (ImportError, AttributeError),
    )
    raises_in_verb(
        "import moo.sdk as sdk\nx = sdk.contextmanager",
        (ImportError, AttributeError),
    )


def test_sdk_log_blocked():
    """

    `log` is the module-level logging.Logger in moo/sdk.py.  Verb code accessing
    it could inject arbitrary strings into the server log via log.info()/log.error().
    BLOCKED_IMPORTS for moo.sdk now includes 'log'.
    """
    raises_in_verb(
        "from moo.sdk import log",
        (ImportError, AttributeError),
    )
    raises_in_verb(
        "import moo.sdk as sdk\nx = sdk.log",
        (ImportError, AttributeError),
    )


# ---------------------------------------------------------------------------
# django_celery_beat not importable even by wizards
# ---------------------------------------------------------------------------


def test_django_celery_beat_not_importable_by_wizards():
    """

    django_celery_beat is not in WIZARD_ALLOWED_MODULES or ALLOWED_MODULES.
    Wizard verb code cannot import django_celery_beat.models directly to
    construct PeriodicTask instances with arbitrary task names outside the
    invoke() guard.  The only creation path is invoke(periodic=True/cron=...),
    which is wizard-gated and always sets task='moo.core.tasks.invoke_verb'.
    """
    raises_in_verb(
        "import django_celery_beat.models",
        ImportError,
        caller=mock_caller(is_wizard=True),
    )


def test_django_celery_beat_not_importable_by_non_wizards():
    """Non-wizards cannot import django_celery_beat either."""
    raises_in_verb("import django_celery_beat.models", ImportError)


# ---------------------------------------------------------------------------
# re module return objects
# ---------------------------------------------------------------------------


def test_re_match_object_attributes_are_safe():
    """

    re.compile(pattern).match(s) returns a Match object.  Its non-underscore
    attributes (group, string, pos, endpos, lastindex, lastgroup, regs) return
    strings, integers, or tuples of integers.  No Django model instances or
    callable chains that could lead to sandbox escape.
    """
    from .utils import exec_verb

    printed = exec_verb(
        "import re\nm = re.match(r'hello', 'hello world')\nprint(m.group())\nprint(m.string)\nprint(m.pos)\n"
    )
    assert printed == ["hello", "hello world", 0]


def test_re_pattern_object_attributes_are_safe():
    """re.compile() returns a Pattern whose public attributes are strings/integers."""
    from .utils import exec_verb

    printed = exec_verb(
        "import re\np = re.compile(r'\\d+')\nprint(p.pattern)\nprint(p.flags > 0)\n"  # pylint: disable=implicit-str-concat
    )
    assert printed == [r"\d+", True]


# ---------------------------------------------------------------------------
# hashlib module return objects
# ---------------------------------------------------------------------------


def test_hashlib_hash_object_attributes_are_safe():
    """

    hashlib.md5(b'data') returns a HASH object.  Its non-underscore attributes
    (digest_size, block_size, name, hexdigest(), digest()) return integers,
    strings, or bytes.  No dangerous object references or callable chains.
    """
    from .utils import exec_verb

    printed = exec_verb(
        "import hashlib\nh = hashlib.md5(b'test')\nprint(isinstance(h.hexdigest(), str))\nprint(h.digest_size)\n"
    )
    assert printed == [True, 16]


# ---------------------------------------------------------------------------
# datetime module return objects
# ---------------------------------------------------------------------------


def test_datetime_instances_are_safe():
    """

    datetime.datetime.now() returns a datetime instance.  Methods like
    replace(), strftime(), and isoformat() return datetime instances or strings.
    No Django model exposure or callable chains to sandbox internals.
    """
    from .utils import exec_verb

    printed = exec_verb(
        "import datetime\n"
        "now = datetime.datetime.now()\n"
        "print(isinstance(now, datetime.datetime))\n"
        "s = now.strftime('%Y')\n"
        "print(isinstance(s, str))\n"
    )
    assert printed == [True, True]


def test_datetime_timedelta_is_safe():
    """datetime.timedelta arithmetic returns timedelta instances — safe."""
    from .utils import exec_verb

    printed = exec_verb(
        "import datetime\ntd = datetime.timedelta(days=1)\nprint(td.days)\nprint(td.seconds)\n"  # pylint: disable=implicit-str-concat
    )
    assert printed == [1, 0]


# ---------------------------------------------------------------------------
# time module return objects
# ---------------------------------------------------------------------------


def test_time_struct_time_is_safe():
    """

    time.gmtime() returns a struct_time — a named-tuple-like object.
    Its attributes (tm_year, tm_mon, tm_mday, etc.) are all integers.
    time.time() returns a float.  No dangerous escalation paths.
    """
    from .utils import exec_verb

    printed = exec_verb(
        "import time\nt = time.gmtime(0)\nprint(t.tm_year)\nprint(isinstance(time.time(), float))\n"  # pylint: disable=implicit-str-concat
    )
    assert printed == [1970, True]
