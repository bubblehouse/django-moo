import pytest

from moo.core.models.object import Object

from .. import code


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_eval_simple_command(t_init: Object, t_wizard: Object):
    def _writer(msg):
        raise RuntimeError("print was called unexpectedly")

    with code.ContextManager(t_wizard, _writer):
        writer = code.ContextManager.get("writer")
        globals = code.get_default_globals()  # pylint: disable=redefined-builtin
        globals.update(code.get_restricted_environment("__main__", writer))
        result = code.do_eval("dir()", {}, globals)
        assert result == []


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_trivial_printing(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer):
        writer = code.ContextManager.get("writer")
        globals = code.get_default_globals()  # pylint: disable=redefined-builtin
        globals.update(code.get_restricted_environment("__main__", writer))
        result = code.do_eval("print('test')", {}, globals)
        assert result is None
        assert printed == ["test"]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_printing_imported_caller(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer):
        writer = code.ContextManager.get("writer")
        globals = code.get_default_globals()  # pylint: disable=redefined-builtin
        globals.update(code.get_restricted_environment("__main__", writer))
        src = "from moo.core import context\nprint(context.caller)"
        code.r_exec(src, {}, globals)
        assert printed == [t_wizard]

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_caller_stack(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.ContextManager(t_wizard, _writer):
        from moo.core import context, lookup, create

        player = lookup("Player")

        # Create 3 new objects to serve as verb owners
        p3 = create("TestPlayer3")
        p4 = create("TestPlayer4")
        p5 = create("TestPlayer5")

        # Build a chain of 5 verbs on the Player class, each owned by a different player.
        # add_verb() sets owner = ContextManager.get("caller") = t_wizard, so we
        # update the owner afterward. Permissions (allow "everyone" "execute") are set
        # automatically by apply_default_permissions during Verb.save() on creation.

        v1 = player.add_verb("test-caller-chain-1", code="""
from moo.core import context
this.invoke_verb("test-caller-chain-2")
""")
        v1.owner = t_wizard
        v1.save()

        v2 = player.add_verb("test-caller-chain-2", code="""
from moo.core import context
this.invoke_verb("test-caller-chain-3")
""")
        v2.owner = player
        v2.save()

        v3 = player.add_verb("test-caller-chain-3", code="""
from moo.core import context
this.invoke_verb("test-caller-chain-4")
""")
        v3.owner = p3
        v3.save()

        v4 = player.add_verb("test-caller-chain-4", code="""
from moo.core import context
this.invoke_verb("test-caller-chain-5")
""")
        v4.owner = p4
        v4.save()

        v5 = player.add_verb("test-caller-chain-5", code="""
from moo.core import context
for frame in context.caller_stack:
    print(frame)
""")
        v5.owner = p5
        v5.save()

        # Invoke the chain
        player.invoke_verb("test-caller-chain-1")

        # Stack is fully unwound after all verbs return
        assert context.caller_stack == []

        # The 5 frames were captured in order by verb 5
        assert printed == [
            dict(caller=t_wizard, origin=player, player=t_wizard, previous_caller=t_wizard, this=player, verb_name="test-caller-chain-1"),
            dict(caller=player, origin=player, player=t_wizard, previous_caller=t_wizard, this=player, verb_name="test-caller-chain-2"),
            dict(caller=p3, origin=player, player=t_wizard, previous_caller=player, this=player, verb_name="test-caller-chain-3"),
            dict(caller=p4, origin=player, player=t_wizard, previous_caller=p3, this=player, verb_name="test-caller-chain-4"),
            dict(caller=p5, origin=player, player=t_wizard, previous_caller=p4, this=player, verb_name="test-caller-chain-5"),
        ]
