import pytest

from moo.core import code, create, lookup
from moo.core.models import Object


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_set_neuter(t_init: Object, t_wizard: Object):
    """Setting gender to 'neuter' assigns neuter pronouns to the object."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        obj = create("test_neuter", parents=[system.thing])
        result = system.gender_utils.set(obj, "neuter")
    assert result == "neuter"
    assert obj.get_property("ps") == "it"
    assert obj.get_property("po") == "it"
    assert obj.get_property("pp") == "its"
    assert obj.get_property("pr") == "itself"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_set_male(t_init: Object, t_wizard: Object):
    """Setting gender to 'male' assigns masculine pronouns to the object."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        obj = create("test_male", parents=[system.thing])
        result = system.gender_utils.set(obj, "male")
    assert result == "male"
    assert obj.get_property("ps") == "he"
    assert obj.get_property("po") == "him"
    assert obj.get_property("pp") == "his"
    assert obj.get_property("pr") == "himself"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_set_female(t_init: Object, t_wizard: Object):
    """Setting gender to 'female' assigns feminine pronouns to the object."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        obj = create("test_female", parents=[system.thing])
        result = system.gender_utils.set(obj, "female")
    assert result == "female"
    assert obj.get_property("ps") == "she"
    assert obj.get_property("po") == "her"
    assert obj.get_property("pp") == "her"
    assert obj.get_property("pr") == "herself"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_set_plural(t_init: Object, t_wizard: Object):
    """Setting gender to 'plural' assigns plural pronouns to the object."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        obj = create("test_plural", parents=[system.thing])
        result = system.gender_utils.set(obj, "plural")
    assert result == "plural"
    assert obj.get_property("ps") == "they"
    assert obj.get_property("po") == "them"
    assert obj.get_property("pp") == "their"
    assert obj.get_property("pr") == "themselves"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_set_unknown_gender_returns_none(t_init: Object, t_wizard: Object):
    """An unrecognised gender string causes set() to return None."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        obj = create("test_unknown", parents=[system.thing])
        result = system.gender_utils.set(obj, "adkjfhadslfjkg")
    assert result is None


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_set_all_pronoun_properties(t_init: Object, t_wizard: Object):
    """set() assigns all ten pronoun properties, including capitalised variants."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        obj = create("test_all_pronouns", parents=[system.thing])
        system.gender_utils.set(obj, "female")
    assert obj.get_property("ps") == "she"
    assert obj.get_property("po") == "her"
    assert obj.get_property("pp") == "her"
    assert obj.get_property("pr") == "herself"
    assert obj.get_property("pq") == "hers"
    assert obj.get_property("psc") == "She"
    assert obj.get_property("poc") == "Her"
    assert obj.get_property("ppc") == "Hers"
    assert obj.get_property("prc") == "Herself"
    assert obj.get_property("pqc") == "Hers"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_set_overwrites_existing_pronouns(t_init: Object, t_wizard: Object):
    """set() replaces previously assigned pronouns when called a second time."""
    with code.ContextManager(t_wizard, lambda msg: None):
        system = lookup(1)
        obj = create("test_overwrite", parents=[system.thing])
        system.gender_utils.set(obj, "male")
        result = system.gender_utils.set(obj, "female")
    assert result == "female"
    assert obj.get_property("ps") == "she"
    assert obj.get_property("pr") == "herself"
