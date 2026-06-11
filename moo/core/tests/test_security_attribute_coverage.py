# -*- coding: utf-8 -*-
"""
Sentinel tests: every public attribute on the sandbox-exposed models must be
classified for read-ACL enforcement.

The sandbox read checks in moo/core/code.py derive field and reverse-relation
names from Model._meta automatically; methods must be declared by hand in
SANDBOX_READ_METHODS (read-checked) or SANDBOX_EXEMPT_METHODS (does its own
ACL check). These tests are the CI tripwire: adding a public field or method
to Object, Verb, or Property without classifying it fails here, instead of
silently skipping the ACL check at runtime.
"""

import pytest

from moo.core.code import (
    SANDBOX_EXEMPT_METHODS,
    SANDBOX_READ_METHODS,
    SANDBOX_SPECIAL_ATTRIBUTES,
    derive_sandbox_field_names,
)
from moo.core.models.object import Object
from moo.core.models.property import Property
from moo.core.models.verb import Verb

# Pure introspection, but session-level autouse fixtures touch the Site table.
pytestmark = pytest.mark.django_db

MODELS = [("object", Object), ("verb", Verb), ("property", Property)]

# Django/ORM machinery; not security-relevant attribute surface. Instance
# access to managers raises in Django itself, and from_db/do_not_call_in_templates
# are framework hooks, not data.
NOISE = frozenset(
    {
        "DoesNotExist",
        "MultipleObjectsReturned",
        "objects",
        "global_objects",
        "from_db",
        "do_not_call_in_templates",
    }
)


def _public_attribute_names(model_cls):
    """Public attributes defined on the model itself (and project mixins),
    skipping classes that belong to Django or builtins."""
    names = set()
    for klass in model_cls.__mro__:
        if klass.__module__.startswith(("django.", "builtins")):
            continue
        names.update(n for n in vars(klass) if not n.startswith("_"))
    return names


@pytest.mark.parametrize("kind,model_cls", MODELS)
def test_model_public_attributes_are_classified(kind, model_cls):
    unclassified = (
        _public_attribute_names(model_cls)
        - derive_sandbox_field_names(model_cls)
        - SANDBOX_READ_METHODS[kind]
        - SANDBOX_EXEMPT_METHODS[kind]
        - SANDBOX_SPECIAL_ATTRIBUTES
        - NOISE
    )
    assert not unclassified, (
        f"Unclassified public attribute(s) on {model_cls.__name__}: {sorted(unclassified)} — "
        f"add to SANDBOX_READ_METHODS[{kind!r}] (read requires the 'read' permission) or "
        f"SANDBOX_EXEMPT_METHODS[{kind!r}] (performs its own ACL check) in moo/core/code.py"
    )


@pytest.mark.parametrize("kind,model_cls", MODELS)
def test_declared_method_names_exist_on_models(kind, model_cls):
    stale = {name for name in SANDBOX_READ_METHODS[kind] | SANDBOX_EXEMPT_METHODS[kind] if not hasattr(model_cls, name)}
    assert not stale, (
        f"SANDBOX_*_METHODS[{kind!r}] entries no longer exist on {model_cls.__name__}: {sorted(stale)} — "
        "remove or rename them in moo/core/code.py"
    )


@pytest.mark.parametrize("kind,model_cls", MODELS)
def test_buckets_are_pairwise_disjoint(kind, model_cls):
    derived = derive_sandbox_field_names(model_cls)
    read_methods = SANDBOX_READ_METHODS[kind]
    exempt = SANDBOX_EXEMPT_METHODS[kind]
    assert not derived & read_methods
    assert not derived & exempt
    assert not read_methods & exempt
    assert not (derived | read_methods | exempt) & SANDBOX_SPECIAL_ATTRIBUTES


def test_derived_fields_include_expected_accessors():
    object_fields = derive_sandbox_field_names(Object)
    # Reverse relations into auth/mail tables must be read-checked even though
    # guard_result blocks their querysets outright for non-wizards.
    assert {"pk", "id", "children", "contents", "player_set", "rights"} <= object_fields
    assert "acl" not in object_fields
    assert not any(name.startswith("_") for name in object_fields)
    assert "names" in derive_sandbox_field_names(Verb)
