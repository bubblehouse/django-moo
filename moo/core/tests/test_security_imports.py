# -*- coding: utf-8 -*-
# pylint: disable=protected-access
"""
Security tests: import blocking.

Covers: ContextManager, _publish_to_player, string module,
moo.core submodules, SDK internal names, module attribute traversal
(passes 1, 2, 3, 4, 7).
"""

from .utils import raises_in_verb


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
