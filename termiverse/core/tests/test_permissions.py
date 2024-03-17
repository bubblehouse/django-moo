import pytest

from termiverse.core.models import Object, Player
from termiverse.tests import *  # pylint: disable=wildcard-import

@pytest.mark.django_db
def test_regular_user_can_read_a_thing(t_init, t_wizard):  # pylint: disable=redefined-outer-name
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
def test_regular_user_who_owns_a_thing(t_init, t_wizard):  # pylint: disable=redefined-outer-name
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
def test_everyone_can_read_a_thing(t_init, t_wizard):  # pylint: disable=redefined-outer-name
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
def test_wizard_can_do_most_things(t_init, t_wizard):  # pylint: disable=redefined-outer-name
    # Objects are only Wizards if they have an associated Player with wizard=True
    Player.objects.create(avatar=t_wizard, wizard=True)
    thing = Object.objects.create(name='thing')
    assert t_wizard.is_allowed('read', thing)
    assert t_wizard.is_allowed('write', thing)
    assert t_wizard.is_allowed('entrust', thing)
    assert t_wizard.is_allowed('move', thing)
    assert t_wizard.is_allowed('transmute', thing)
    assert t_wizard.is_allowed('derive', thing)
    assert t_wizard.is_allowed('develop', thing)

@pytest.mark.django_db
def test_add_a_simple_deny_clase(t_init, t_wizard):  # pylint: disable=redefined-outer-name
    user = Object.objects.get(name__iexact='player')
    thing = Object.objects.create(name='thing', owner=user)
    thing.allow('everyone', 'anything')
    thing.deny(user, 'write')

    assert user.is_allowed('read', thing)
    assert not user.is_allowed('write', thing)
