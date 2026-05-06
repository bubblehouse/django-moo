# -*- coding: utf-8 -*-
"""
Support resources for PyTest framework.
"""

import importlib.resources
import logging

import pytest
from django.conf import settings
from django.contrib.auth.models import User  # pylint: disable=imported-auth-user

from moo.bootstrap import load_python
from moo.core.models import Object, Player, Repository

log = logging.getLogger(__name__)


@pytest.fixture(autouse=True, scope="session")
def configure_celery_for_tests():
    from moo.celery import app

    app.conf.update(
        broker_url="memory://",
        task_always_eager=True,
        task_store_eager_result=True,
    )


@pytest.fixture(autouse=True)
def mock_player_connected(monkeypatch):
    """Patch is_connected to return True for all objects during tests.

    In production, is_connected() checks a Redis cache key set by the SSH shell.
    That key is never set during tests, so without this patch every player avatar
    appears disconnected and tell() / write() never fires.
    """
    monkeypatch.setattr(Object, "is_connected", lambda self: True)


@pytest.fixture(autouse=True)
def _reset_site_context():
    """Drop any leaked site/contextvar/Site-cache state between tests.

    ``ContextVar`` and ``Site.objects`` caches are process-level — a test
    that sets ``ContextManager.set_site(siteX)`` or holds a reference to a
    rolled-back Site row would otherwise leak into the next test's setup.
    """
    from django.contrib.sites.models import Site

    from moo.core.code import ContextManager

    ContextManager.set_site(None)
    Site.objects.clear_cache()
    yield
    ContextManager.set_site(None)
    Site.objects.clear_cache()


@pytest.fixture()
def t_init(request):
    """
    Test fixture that pre-seeds a basic bootstrapped environment.
    """
    from django.contrib.sites.models import Site

    from moo.core.moojson import clear_nothing_cache

    clear_nothing_cache()
    # Django caches the per-process Site lookup; tests that create or roll
    # back Site rows can leave a stale instance in that cache and trigger
    # FK violations when a later test tries to use it.
    Site.objects.clear_cache()
    name = request.param if hasattr(request, "param") else "test"
    log.debug(f"t_init: {name}")
    # Fast path: if a tx-mode test with ``serialized_rollback=True`` just
    # restored the post-bootstrap snapshot from ``moo.bootstrap`` migrations,
    # both the Repository row and System Object are already present.  Walking
    # 196+ verb files only to confirm they're already there is what dominates
    # per-test setup time on the ``default`` bootstrap; skip it.
    if Repository.objects.filter(slug=name).exists() and Object.global_objects.filter(pk=1).exists():
        yield Object.global_objects.get(pk=1)
        clear_nothing_cache()
        return
    Repository.objects.get_or_create(
        slug=name,
        defaults={"prefix": f"moo/bootstrap/{name}/verbs", "url": settings.DEFAULT_GIT_REPO_URL},
    )
    pkg = importlib.resources.files("moo.bootstrap")
    pkg_script = pkg / name / "bootstrap.py"
    pkg_flat = pkg / f"{name}.py"
    ref = pkg_script if (pkg / name).is_dir() else pkg_flat
    with importlib.resources.as_file(ref) as path:
        load_python(path)
    yield Object.objects.get(id=1)
    clear_nothing_cache()


def pytest_collection_modifyitems(config, items):  # pylint: disable=unused-argument
    """Add ``serialized_rollback=True`` to tx tests using the ``default`` dataset.

    The ``moo.bootstrap`` seed migration loads ``default/bootstrap.py`` once
    during test DB setup; pytest-django serializes that state.  Tests
    parametrized with ``t_init=["default"]`` benefit from restoring the
    snapshot rather than re-running ``load_python`` per test.

    Tests using the minimal ``test`` dataset (or no parametrize) don't get
    the marker — deserializing the full default snapshot is slower than
    running ``test.py`` AND would change their semantics (they'd see the
    full default world instead of a minimal sentinel-only DB).  Tests
    parametrized to a non-default dataset also opt out.

    Tests that must run against a freshly-uninitialized DB (i.e. test the
    bootstrap mechanism itself) opt out via ``pytestmark.no_default_snapshot``;
    the loop below honors that opt-out.
    """
    for item in items:
        if item.get_closest_marker("no_default_snapshot") is not None:
            continue
        callspec = getattr(item, "callspec", None)
        if callspec is None or callspec.params.get("t_init") != "default":
            continue
        for marker in item.iter_markers(name="django_db"):
            if marker.kwargs.get("transaction"):
                marker.kwargs["serialized_rollback"] = True


@pytest.fixture(autouse=True, scope="session")
def _patch_django_test_teardown(django_db_setup, django_db_blocker):
    """Stabilize content_type PKs and patch tx-test teardown for snapshot use.

    Two collaborating fixes:

    1. **Stabilize the snapshot.**  ``app_config.get_models()`` returns models
       in a *different order* during initial ``migrate`` than during a
       subsequent ``flush + emit_post_migrate``, which means
       ``bulk_create`` of content_types assigns different PKs (e.g.
       ``django_celery_beat.crontabschedule`` lands at PK 8 initially but
       PK 11 post-flush).  pytest-django's ``serialize_db_to_string`` runs
       at the end of ``setup_databases`` and captures the *initial-migrate*
       order, so any later ``deserialize`` collides on the UNIQUE
       ``(app_label, model)`` constraint.  We do one ``flush + post_migrate``
       cycle now, then re-serialize — locking in the post-flush order so the
       snapshot matches every subsequent flush.

    2. **Patch ``TransactionTestCase._fixture_teardown``** to use
       ``reset_sequences=True, inhibit_post_migrate=False`` universally.
       Django's default (``reset_sequences=False``) lets autoincrement drift
       higher across tests, also breaking deserialize PK alignment.  And the
       conditional ``inhibit_post_migrate=True`` for
       ``serialized_rollback`` tests leaves the default Site empty after
       teardown, crashing ``get_default_site()`` in the next test.  Forcing
       ``reset_sequences=True, inhibit_post_migrate=False`` always leaves
       the DB in a consistent post-migrate baseline that lines up with the
       snapshot's post-flush order.
    """
    from django.core.management import call_command
    from django.db import connection
    from django.test import testcases

    # Step 1: re-baseline the snapshot to post-flush content_type order.
    with django_db_blocker.unblock():
        call_command(
            "flush",
            verbosity=0,
            interactive=False,
            database=connection.alias,
            reset_sequences=True,
            inhibit_post_migrate=False,
        )
        # Re-run the bootstrap so the snapshot has both the post-flush
        # content_types AND the bootstrap data the seed migration added.
        ref = importlib.resources.files("moo.bootstrap") / "default" / "bootstrap.py"
        with importlib.resources.as_file(ref) as path:
            load_python(path)
        connection._test_serialized_contents = (  # pylint: disable=protected-access
            connection.creation.serialize_db_to_string()
        )

    # Step 2: patch tx-test teardown.
    original_teardown = testcases.TransactionTestCase._fixture_teardown  # pylint: disable=protected-access

    def patched_teardown(self):
        for db_name in self._databases_names(include_mirrors=False):  # pylint: disable=protected-access
            call_command(
                "flush",
                verbosity=0,
                interactive=False,
                database=db_name,
                reset_sequences=True,
                allow_cascade=self.available_apps is not None,
                inhibit_post_migrate=False,
            )

    testcases.TransactionTestCase._fixture_teardown = patched_teardown  # pylint: disable=protected-access

    yield

    testcases.TransactionTestCase._fixture_teardown = original_teardown  # pylint: disable=protected-access


@pytest.fixture()
def t_wizard():
    """
    Test fixture that returns the Wizard account.
    """
    yield Object.objects.get(name="Wizard")


@pytest.fixture()
def t_wizard_user_pk(t_wizard):
    """
    Django User PK for the Wizard avatar.

    Session settings (``_session_settings``, ``moo:session:*`` cache keys)
    are keyed by Django User PK — not Object PK — so tests that pre-populate
    the registry must use this PK, not ``t_wizard.owner.pk``.
    """
    yield Player.objects.filter(avatar=t_wizard).select_related("user").first().user.pk


@pytest.fixture()
def t_two_sites():
    """
    Bootstrap two independent universes (Site 1 + a second Site) and yield
    ``(site1, site2)``. Uses the ``test`` dataset on each site so the basic
    System/Wizard/sentinel objects exist.  Tests that need ``$root_class``,
    ``$player``, etc. should depend on a full bootstrap fixture instead.
    """
    from django.contrib.sites.models import Site

    from moo.bootstrap import initialize_dataset
    from moo.core.code import ContextManager
    from moo.core.moojson import clear_nothing_cache

    clear_nothing_cache()
    site1, _ = Site.objects.get_or_create(pk=1, defaults={"domain": "site1.test", "name": "site1"})
    site2 = Site.objects.create(domain="site2.test", name="site2")
    initialize_dataset("test", site=site1)
    initialize_dataset("test", site=site2)
    # Reset to no site so each test can pick its own context.
    ContextManager.set_site(None)
    yield site1, site2
    clear_nothing_cache()


@pytest.fixture()
def t_two_sites_default():
    """
    Like ``t_two_sites`` but loads the full ``default`` bootstrap on each site
    so the system-property graph (``$root_class``, ``$player``, etc.) is
    populated. Slower; use only when the test actually probes those properties.
    """
    from django.contrib.sites.models import Site

    from moo.core.code import ContextManager
    from moo.core.moojson import clear_nothing_cache

    clear_nothing_cache()
    site1, _ = Site.objects.get_or_create(pk=1, defaults={"domain": "site1.test", "name": "site1"})
    site2 = Site.objects.create(domain="site2.test", name="site2")
    pkg = importlib.resources.files("moo.bootstrap")
    pkg_script = pkg / "default" / "bootstrap.py"
    for site in (site1, site2):
        ContextManager.set_site(site)
        with importlib.resources.as_file(pkg_script) as path:
            load_python(path)
    ContextManager.set_site(None)
    yield site1, site2
    clear_nothing_cache()
