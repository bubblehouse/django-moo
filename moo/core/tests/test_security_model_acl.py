# -*- coding: utf-8 -*-
# pylint: disable=protected-access
"""
Security tests: Access (ACL) and Repository model permission checks.

Covers Access.save / .delete grant enforcement (including the
attacker-rebinds-row-FK attack) and the Repository.save wizard guard,
which fires regardless of whether Repository is reached via verb.repo
or imported directly.
"""

import pytest

from moo.core.models.object import Object

from .utils import ctx, mock_caller

# ---------------------------------------------------------------------------
# Access.save() / Access.delete() must require grant permission
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_access_save_requires_grant(t_init: Object, t_wizard: Object):
    """

    Access.save() previously had no permission check. A non-wizard with grant
    on their own object could obtain an Access row, reassign its object FK to
    a wizard-owned object, then call save() to inject an ACL entry without
    having grant on the target. Access.save() now calls can_caller("grant")
    against the entity the row belongs to.
    """
    from moo.sdk import create
    from moo.core.exceptions import AccessError

    with ctx(t_wizard):
        attacker = create("acl_save_attacker")
        target = create("acl_save_target")
        attacker.allow(attacker, "grant")
        attacker.allow("everyone", "read")

    access = attacker.acl.filter(group="everyone").first()
    assert access is not None

    access.object = target

    with ctx(attacker):
        with pytest.raises((PermissionError, AccessError)):
            access.save()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_access_save_new_entry_requires_grant(t_init: Object, t_wizard: Object):
    """

    Creating a new Access row directly (bypassing allow()/deny()) must require
    grant on the target entity. Previously Access.save() had no check, so any
    caller could insert arbitrary ACL rows.
    """
    from moo.sdk import create
    from moo.core.exceptions import AccessError
    from moo.core.models.acl import Access, Permission

    with ctx(t_wizard):
        plain = create("acl_new_plain")
        protected = create("acl_new_protected")

    perm = Permission.objects.get(name="read")

    with ctx(plain):
        with pytest.raises((PermissionError, AccessError)):
            Access(
                object=protected,
                rule="allow",
                permission=perm,
                type="group",
                group="everyone",
            ).save()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_access_delete_requires_grant(t_init: Object, t_wizard: Object):
    """

    Access.delete() previously had no permission check. Without it an attacker
    could delete ACL entries on objects they have no grant over. Access.delete()
    now calls can_caller("grant") on the entity the row belongs to.
    """
    from moo.sdk import create
    from moo.core.exceptions import AccessError

    with ctx(t_wizard):
        plain = create("acl_del_plain")
        protected = create("acl_del_protected")
        protected.allow("everyone", "read")

    access = protected.acl.filter(group="everyone").first()
    assert access is not None

    with ctx(plain):
        with pytest.raises((PermissionError, AccessError)):
            access.delete()

    assert protected.acl.filter(group="everyone").exists()


# ---------------------------------------------------------------------------
# Repository.save() must require wizard
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_repository_save_requires_wizard(t_init: Object, t_wizard: Object):
    """

    Repository.save() previously had no permission check. A non-wizard with
    read access to a verb could reach verb.repo and overwrite the URL,
    redirecting future verb.reload() fetches to an attacker-controlled source.
    Repository.save() now raises AccessError for non-wizard callers.
    """
    from moo.sdk import create
    from moo.core.exceptions import AccessError
    from moo.core.models.verb import Repository

    with ctx(t_wizard):
        plain = create("repo_save_plain")
        target = create("repo_save_target")
        repo = Repository(slug="test-repo", url="https://gitlab.com/test/repo.git", prefix="verbs/")
        repo.save()
        target.add_verb("repo_verb", code='print("ok")', repo=repo, filename="verbs/repo_verb.py")
        target.allow(plain, "read")

    verb = target.verbs.filter(names__name="repo_verb").first()
    assert verb is not None
    assert verb.repo is not None

    with ctx(plain):
        with pytest.raises((PermissionError, AccessError)):
            verb.repo.url = "https://attacker.example.com/evil.git"
            verb.repo.save()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_repository_save_wizard_guard_fires_via_direct_import(t_init: Object, t_wizard: Object):
    """

    Repository.save() checks ContextManager.get('caller').is_wizard() directly,
    not call-site restrictions.  This guard fires whether Repository is accessed
    via verb.repo or by a wizard importing moo.core.models.verb directly.

    Non-wizard callers must always be rejected.  Wizard callers may save, which
    is acceptable: WIZARD_ALLOWED_MODULES allows moo.core.models.verb and wizards
    are system administrators with full system access.
    """
    from moo.core.models.verb import Repository
    from moo.core.exceptions import AccessError

    plain = mock_caller(is_wizard=False)

    with ctx(plain):
        r = Repository(slug="test-repo-guard", url="https://example.com/repo.git", prefix="verbs/")
        with pytest.raises(AccessError):
            r.save()
