# -*- coding: utf-8 -*-
"""
Support resources for PyTest framework.
"""

import importlib.resources
import logging

import pytest
from django.conf import settings
from django.contrib.auth.models import User  # pylint: disable=imported-auth-user

from moo.core.bootstrap import load_python
from moo.core.models import Object, Player, Repository

log = logging.getLogger(__name__)


@pytest.fixture()
def t_init(request):
    """
    Test fixture that pre-seeds a basic bootstrapped environment.
    """
    name = request.param if hasattr(request, "param") else "test"
    log.debug(f"t_init: {name}")
    Repository.objects.create(slug=name, prefix=f"moo/core/bootstrap/{name}_verbs", url=settings.DEFAULT_GIT_REPO_URL)
    ref = importlib.resources.files("moo.core.bootstrap") / f"{name}.py"
    with importlib.resources.as_file(ref) as path:
        load_python(path)
    user = User.objects.create(username="phil")
    avatar = Object.objects.get(name="Wizard")
    Player.objects.create(user=user, avatar=avatar)
    yield Object.objects.get(id=1)


@pytest.fixture()
def t_wizard():
    """
    Test fixture that returns the Wizard account.
    """
    yield Object.objects.get(name="Wizard")
