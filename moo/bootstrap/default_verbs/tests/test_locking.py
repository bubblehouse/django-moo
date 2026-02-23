import pytest

from moo.core import code, lookup, create
from moo.core.models import Object


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_parse_keyexp(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer):
        system = lookup(1)
        lock_utils = system.get_property("lock_utils")
        assert lock_utils is not None

        # Example 1: simple object number
        keyexp = "#123"
        key = lock_utils.parse_keyexp(keyexp)
        assert key == 123

        # Example 3: two objects
        keyexp = "#12 || #34"
        key = lock_utils.parse_keyexp(keyexp)
        assert key == ["||", 12, 34]

        # Example 4: negation
        keyexp = "!#56"
        key = lock_utils.parse_keyexp(keyexp)
        assert key == ["!", 56]

        # Example from docs:
        keyexp = "#45 && ?#46 && (#47 || !#48)"
        key = lock_utils.parse_keyexp(keyexp)
        assert key == ["&&", ["&&", 45, ["?", 46]], ["||", 47, ["!", 48]]]

@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_eval_key(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer):
        system = lookup(1)
        lock_utils = system.get_property("lock_utils")
        assert lock_utils is not None

        # direct object matches
        assert lock_utils.eval_key(15, lookup(15)) is True
        assert lock_utils.eval_key(["!", 16], lookup(16)) is False
        assert lock_utils.eval_key(["!", 16], lookup(15)) is False
        assert lock_utils.eval_key(["||", 3, 4], lookup(3)) is True
        assert lock_utils.eval_key(["||", 3, 4], lookup(5)) is False

        # test the "?" operator
        assert lock_utils.eval_key(["?", 10], lookup(10)) is False  # not present
        system.set_property("key", 10)
        system.save()
        assert lock_utils.eval_key(["?", 1], lookup(10)) is True

        player = lookup("Player")
        thing1 = create("thing1", parents=[system.thing], location=player)
        thing2 = create("thing2", parents=[system.thing], location=player)
        assert lock_utils.eval_key(["&&", thing1.id, thing2.id], t_wizard) is False
        assert lock_utils.eval_key(["&&", thing1.id, thing2.id], player) is True
