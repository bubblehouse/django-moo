import pytest

from moo.core import code, lookup, create
from moo.core.models import Object


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_parse_keyexp(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer):
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
def test_eval_key_direct_match(t_init: Object, t_wizard: Object):
    """eval_key with an integer key returns True only for the matching object."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer):
        system = lookup(1)
        lock_utils = system.get_property("lock_utils")
        assert lock_utils is not None

        obj = create("lock_target", parents=[system.thing])
        other = create("lock_other", parents=[system.thing])

        assert lock_utils.eval_key(obj.id, obj) is True
        assert lock_utils.eval_key(obj.id, other) is False


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_eval_key_not(t_init: Object, t_wizard: Object):
    """! negates the result; containment also satisfies the underlying check."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer):
        system = lookup(1)
        lock_utils = system.get_property("lock_utils")
        assert lock_utils is not None

        container = create("lock_container", parents=[system.container])
        # item is inside container, so container.contains(item) is True
        item = create("lock_item", parents=[system.thing], location=container)

        # candidate is the item itself: not (item == item) → False
        assert lock_utils.eval_key(["!", item.id], item) is False
        # candidate is the container: not (container.contains(item)) → False
        assert lock_utils.eval_key(["!", item.id], container) is False
        # unrelated candidate: not False → True
        assert lock_utils.eval_key(["!", item.id], t_wizard) is True


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_eval_key_or(t_init: Object, t_wizard: Object):
    """|| returns True if either operand matches the candidate."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer):
        system = lookup(1)
        lock_utils = system.get_property("lock_utils")
        assert lock_utils is not None

        obj_a = create("lock_or_a", parents=[system.thing])
        obj_b = create("lock_or_b", parents=[system.thing])
        obj_c = create("lock_or_c", parents=[system.thing])

        assert lock_utils.eval_key(["||", obj_a.id, obj_b.id], obj_a) is True
        assert lock_utils.eval_key(["||", obj_a.id, obj_b.id], obj_b) is True
        assert lock_utils.eval_key(["||", obj_a.id, obj_b.id], obj_c) is False


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_eval_key_and(t_init: Object, t_wizard: Object):
    """&& returns True only when the candidate contains both referenced objects."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer):
        system = lookup(1)
        lock_utils = system.get_property("lock_utils")
        assert lock_utils is not None

        carrier = create("lock_carrier", parents=[system.container])
        thing1 = create("lock_thing1", parents=[system.thing], location=carrier)
        thing2 = create("lock_thing2", parents=[system.thing], location=carrier)

        # carrier holds both items
        assert lock_utils.eval_key(["&&", thing1.id, thing2.id], carrier) is True
        # t_wizard holds neither
        assert lock_utils.eval_key(["&&", thing1.id, thing2.id], t_wizard) is False


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_eval_key_question(t_init: Object, t_wizard: Object):
    """? evaluates the .key property of the referenced object against the candidate."""
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer):
        system = lookup(1)
        lock_utils = system.get_property("lock_utils")
        assert lock_utils is not None

        key_holder = create("lock_key_holder", parents=[system.thing])
        candidate = create("lock_candidate", parents=[system.thing])

        # key_holder has no key property yet → False
        assert lock_utils.eval_key(["?", key_holder.id], candidate) is False

        # give key_holder a key that matches candidate
        key_holder.set_property("key", candidate.id)
        key_holder.save()
        assert lock_utils.eval_key(["?", key_holder.id], candidate) is True
