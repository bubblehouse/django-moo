import pytest

from moo.core.models.object import Object
from moo.tests import *  # pylint: disable=wildcard-import
from moo.core import parse

@pytest.mark.django_db
def test_parse(t_init: Object, t_wizard: Object):
    bag = t_wizard.find('bag of holding')[0]
    bag.aliases.create(alias='bag')
    Object.objects.create(name="tongs", location=bag)
    nook = Object.objects.create(name="nook under stairs", location=t_wizard.location)
    Object.objects.create(name="bag", location=nook)

    parser = parse.SpacyParser(
        t_wizard,
        "take the bag from 'nook under stairs' with tongs in wizard's bag"
    )
    assert parser.words._.objects == [nook, bag]
