import importlib.resources

import pytest
from django.contrib.auth.models import User  # pylint: disable=imported-auth-user
from django.conf import settings

from moo.core.models import Repository, Object, Player
from moo.core.bootstrap import load_python

@pytest.fixture()
def t_init():
    name = "test"
    Repository.objects.create(
        slug=name,
        prefix=f'moo/core/bootstrap/{name}_verbs',
        url=settings.DEFAULT_GIT_REPO_URL
    )
    ref = importlib.resources.files('moo.core.bootstrap') / f'{name}.py'
    with importlib.resources.as_file(ref) as path:
        load_python(path)
    user = User.objects.create(username='phil')
    avatar = Object.objects.get(name='Wizard')
    Player.objects.create(user=user, avatar=avatar)
    yield Object.objects.get(id=1)

@pytest.fixture()
def t_wizard():
    yield Object.objects.get(name='Wizard')
