import pytest

from moo.core import code, lookup, parse
from moo.core.models import Object, Verb


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
