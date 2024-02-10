import importlib.resources

from termiverse.core.models import Repository, Object, Player
from termiverse.core.bootstrap import load_python

import pytest
from django.contrib.auth.models import User
from django.conf import settings

@pytest.fixture()
def t_init():
    name = "default"
    Repository.objects.create(
        slug=name,
        prefix=f'termiverse/core/bootstrap/{name}_verbs',
        url=settings.DEFAULT_GIT_REPO_URL
    )
    ref = importlib.resources.files('termiverse.core.bootstrap') / f'{name}.py'
    with importlib.resources.as_file(ref) as path:
        load_python(path)
    user = User.objects.create(username='phil')
    avatar = Object.objects.get(name='Wizard')
    Player.objects.create(user=user, avatar=avatar)
    yield Object.objects.get(id=1)

@pytest.fixture()
def t_wizard():
    yield Object.objects.get(name='Wizard')
