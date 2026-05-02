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
    Repository.objects.create(slug=name, prefix=f"moo/bootstrap/{name}_verbs", url=settings.DEFAULT_GIT_REPO_URL)
    pkg = importlib.resources.files("moo.bootstrap")
    pkg_init = pkg / name / "__init__.py"
    pkg_flat = pkg / f"{name}.py"
    ref = pkg_init if (pkg / name).is_dir() else pkg_flat
    with importlib.resources.as_file(ref) as path:
        load_python(path)
    yield Object.objects.get(id=1)
    clear_nothing_cache()


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
    pkg_init = pkg / "default" / "__init__.py"
    for site in (site1, site2):
        ContextManager.set_site(site)
        with importlib.resources.as_file(pkg_init) as path:
            load_python(path)
    ContextManager.set_site(None)
    yield site1, site2
    clear_nothing_cache()
