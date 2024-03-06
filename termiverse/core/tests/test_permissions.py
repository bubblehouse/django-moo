from termiverse.core.models.object import Object
from termiverse.tests import *

import pytest

@pytest.mark.django_db
def test_defaults(t_init, t_wizard):
    thing = Object.objects.create(name='thing', owner=t_wizard)
    user = Object.objects.get(name__iexact='player')
    assert user.is_allowed('read', thing)
    assert not user.is_allowed('write', thing)
    assert not user.is_allowed('entrust', thing)
    assert not user.is_allowed('move', thing)
    assert not user.is_allowed('transmute', thing)
    assert not user.is_allowed('derive', thing)
    assert not user.is_allowed('develop', thing)

@pytest.mark.django_db
def test_owner_defaults(t_init, t_wizard):
    user = Object.objects.get(name__iexact='player')
    thing = Object.objects.create(name='thing', owner=user)
    assert user.is_allowed('read', thing)
    assert user.is_allowed('write', thing)
    assert user.is_allowed('entrust', thing)
    assert user.is_allowed('move', thing)
    assert user.is_allowed('transmute', thing)
    assert user.is_allowed('derive', thing)
    assert user.is_allowed('develop', thing)

@pytest.mark.django_db
def test_everyone_defaults(t_init, t_wizard):
    thing = Object.objects.create(name='thing')
    jim = Object.objects.create(name='Jim', unique_name=True)
    assert jim.is_allowed('read', thing)
    assert not jim.is_allowed('write', thing)
    assert not jim.is_allowed('entrust', thing)
    assert not jim.is_allowed('move', thing)
    assert not jim.is_allowed('transmute', thing)
    assert not jim.is_allowed('derive', thing)
    assert not jim.is_allowed('develop', thing)

@pytest.mark.django_db
def test_wizard_defaults(t_init, t_wizard):
    thing = Object.objects.create(name='thing')
    assert t_wizard.is_allowed('read', thing)
    assert t_wizard.is_allowed('write', thing)
    assert t_wizard.is_allowed('entrust', thing)
    assert t_wizard.is_allowed('move', thing)
    assert t_wizard.is_allowed('transmute', thing)
    assert t_wizard.is_allowed('derive', thing)
    assert t_wizard.is_allowed('develop', thing)

@pytest.mark.django_db
def test_simple_deny(t_init, t_wizard):
    user = Object.objects.get(name__iexact='player')
    thing = Object.objects.create(name='thing', owner=user)
    thing.allow('everyone', 'anything')
    thing.deny(user, 'write')

    assert user.is_allowed('read', thing)
    assert user.is_allowed('write', thing)
