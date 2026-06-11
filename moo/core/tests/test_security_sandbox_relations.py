# -*- coding: utf-8 -*-
"""
Security tests: sandbox traversal across Django relations.

These cover attack paths where verb code starts with a legitimate MOO Object
and then walks Django reverse relations or foreign keys into raw auth, site,
mail, or parser metadata rows.
"""

import pytest

from moo.core import code
from moo.core.models.auth import Player
from moo.core.models.object import Object

from .utils import ctx


def run_in_sandbox(src, caller, player=None, extra_globals=None):
    """Execute verb source with the same restricted globals used by verbs."""
    printed = []
    with code.ContextManager(caller, printed.append, player=player or caller):
        writer = code.ContextManager.get("writer")
        globals_dict = code.get_default_globals()
        globals_dict.update(code.get_restricted_environment("__main__", writer))
        if extra_globals:
            globals_dict.update(extra_globals)
        code.r_exec(src, {}, globals_dict)
    return printed


def create_player_avatar(owner, name, username, password="OldPassword1!"):
    """Create a MOO Object plus Django auth Player row outside the sandbox."""
    from django.contrib.auth import get_user_model
    from moo.sdk import create

    with ctx(owner):
        avatar = create(name)
    user = get_user_model().objects.create_user(username=username, password=password)
    Player.objects.create(user=user, avatar=avatar, site=avatar.site, wizard=False)
    return avatar, user


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_player_reverse_relation_cannot_escalate_to_wizard(t_init: Object, t_wizard: Object):
    """A player-owned verb cannot reach Player/User rows through avatar.player_set."""
    attacker, user = create_player_avatar(t_wizard, "relation_auth_attacker", "relation-auth-attacker")

    src = """
from moo.sdk import context
row = context.player.player_set.all().first()
row.wizard = True
row.user.is_staff = True
row.user.is_superuser = True
row.user.set_password("NewPassword2@")
row.user.save()
row.save()
"""
    with pytest.raises(AttributeError):
        run_in_sandbox(src, attacker)

    player_row = Player.objects.get(avatar=attacker)
    user.refresh_from_db()
    assert player_row.wizard is False
    assert user.is_staff is False
    assert user.is_superuser is False
    assert user.check_password("OldPassword1!")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_site_foreign_key_is_not_exposed_to_non_wizard_verbs(t_init: Object, t_wizard: Object):
    """Object.site must not hand a mutable django.contrib.sites Site to verb code."""
    attacker, _user = create_player_avatar(t_wizard, "relation_site_attacker", "relation-site-attacker")
    original_domain = attacker.site.domain

    src = """
from moo.sdk import context
site = context.player.site
site.domain = "hijacked.example"
site.save()
"""
    with pytest.raises(AttributeError):
        run_in_sandbox(src, attacker)

    attacker.site.refresh_from_db()
    assert attacker.site.domain == original_domain


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_unsafe_model_instances_are_blocked_even_when_in_globals(t_init: Object, t_wizard: Object):
    """A raw UserKey passed into globals cannot be inspected or mutated by sandbox code."""
    attacker, user = create_player_avatar(t_wizard, "relation_key_attacker", "relation-key-attacker")
    key = make_user_key(user)

    src = """
key.fingerprint = "changed"
key.save()
"""
    with pytest.raises(AttributeError):
        run_in_sandbox(src, attacker, extra_globals={"key": key})

    key.refresh_from_db()
    assert key.fingerprint != "changed"


def make_user_key(user):
    """Create a UserKey row outside the sandbox."""
    from simplesshkey.models import UserKey

    key = UserKey(
        user=user, key="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIENECd0+5MZVjAq4I1m1Am9zev/A309sk6dcxFiwnXEb test"
    )
    key.full_clean()
    key.save()
    return key


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_iteration_yields_are_guarded_for_non_wizard(t_init: Object, t_wizard: Object):
    """A plain list of restricted model rows must not yield instances to a loop."""
    attacker, user = create_player_avatar(t_wizard, "relation_iter_attacker", "relation-iter-attacker")
    key = make_user_key(user)

    src = """
for k in keys:
    pass
"""
    with pytest.raises(AttributeError):
        run_in_sandbox(src, attacker, extra_globals={"keys": [key]})


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_comprehension_yields_are_guarded_for_non_wizard(t_init: Object, t_wizard: Object):
    """Comprehensions iterate via _getiter_ too; yields must be guarded."""
    attacker, user = create_player_avatar(t_wizard, "relation_comp_attacker", "relation-comp-attacker")
    key = make_user_key(user)

    src = """
hits = [k for k in keys]
"""
    with pytest.raises(AttributeError):
        run_in_sandbox(src, attacker, extra_globals={"keys": [key]})


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_iteration_of_sandbox_objects_still_allowed(t_init: Object, t_wizard: Object):
    """Looping over readable MOO Objects keeps working."""
    attacker, _user = create_player_avatar(t_wizard, "relation_iter_reader", "relation-iter-reader")

    with ctx(t_wizard):
        from moo.sdk import create

        things = [create("relation_iter_thing_one"), create("relation_iter_thing_two")]

    src = """
for thing in things:
    print(thing.name)
"""
    printed = run_in_sandbox(src, attacker, extra_globals={"things": things})
    assert printed == ["relation_iter_thing_one", "relation_iter_thing_two"]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_wizard_can_iterate_restricted_instances(t_init: Object, t_wizard: Object):
    """Wizards keep raw access to non-sandbox model rows."""
    _attacker, user = create_player_avatar(t_wizard, "relation_iter_wizard", "relation-iter-wizard")
    key = make_user_key(user)

    src = """
for k in keys:
    pass
"""
    run_in_sandbox(src, t_wizard, extra_globals={"keys": [key]})


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_print_redacts_restricted_model_instances(t_init: Object, t_wizard: Object):
    """print() of a restricted model instance must not leak its __str__."""
    attacker, user = create_player_avatar(t_wizard, "relation_print_attacker", "relation-print-attacker")
    key = make_user_key(user)

    printed = run_in_sandbox("print(key)", attacker, extra_globals={"key": key})

    assert printed == ["<UserKey (restricted)>"]
    output = "\n".join(printed)
    assert key.fingerprint not in output
    assert "AAAAC3" not in output


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_print_shows_restricted_model_to_wizard(t_init: Object, t_wizard: Object):
    """Wizards see the real str() of non-sandbox model instances."""
    _attacker, user = create_player_avatar(t_wizard, "relation_print_wizard", "relation-print-wizard")
    key = make_user_key(user)

    printed = run_in_sandbox("print(key)", t_wizard, extra_globals={"key": key})

    assert printed == [str(key)]
    assert "restricted" not in printed[0]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_mailbox_sdk_is_bound_to_active_player(t_init: Object, t_wizard: Object):
    """A non-wizard player cannot read another player's mailbox via get_mailbox()."""
    from moo.core.exceptions import UserError
    from moo.sdk import send_message

    attacker, _attacker_user = create_player_avatar(t_wizard, "relation_mail_attacker", "relation-mail-attacker")
    victim, _victim_user = create_player_avatar(t_wizard, "relation_mail_victim", "relation-mail-victim")

    with ctx(t_wizard):
        send_message(t_wizard, [victim], "Secret subject", "SECRET BODY")

    src = f"""
from moo.sdk import get_mailbox, lookup
victim = lookup({victim.pk})
print(get_mailbox(victim)[0].message.body)
"""
    with pytest.raises(UserError):
        run_in_sandbox(src, attacker)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_mail_reverse_relations_are_not_exposed(t_init: Object, t_wizard: Object):
    """received_messages/sent_messages must not expose raw mail ORM rows."""
    from moo.sdk import send_message

    attacker, _attacker_user = create_player_avatar(t_wizard, "relation_mail_reverse_attacker", "mail-reverse-attacker")
    victim, _victim_user = create_player_avatar(t_wizard, "relation_mail_reverse_victim", "mail-reverse-victim")

    with ctx(t_wizard):
        send_message(t_wizard, [victim], "Secret subject", "SECRET BODY")

    src = f"""
from moo.sdk import lookup
victim = lookup({victim.pk})
rows = victim.received_messages.all()
"""
    with pytest.raises(AttributeError):
        run_in_sandbox(src, attacker)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_send_message_cannot_spoof_sender_for_non_wizard_player(t_init: Object, t_wizard: Object):
    """send_message() binds non-wizard sends to context.player."""
    from moo.core.exceptions import UserError
    from moo.core.models.mail import Message

    attacker, _attacker_user = create_player_avatar(t_wizard, "relation_mail_spoof_attacker", "mail-spoof-attacker")
    victim, _victim_user = create_player_avatar(t_wizard, "relation_mail_spoof_victim", "mail-spoof-victim")

    src = f"""
from moo.sdk import lookup, send_message
send_message(lookup({t_wizard.pk}), [lookup({victim.pk})], "Forged", "body")
"""
    with pytest.raises(UserError):
        run_in_sandbox(src, attacker)

    assert not Message.objects.filter(subject="Forged").exists()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_read_denial_blocks_fields_and_relations(t_init: Object, t_wizard: Object):
    """Object.name and relation managers must honor the object's read ACL."""
    from moo.core.exceptions import AccessError
    from moo.sdk import create

    with ctx(t_wizard):
        target = create("relation_hidden_object")
        plain = create("relation_hidden_reader")
        target.deny(plain, "read")

    src = f"""
from moo.sdk import lookup
obj = lookup({target.pk})
print(obj.name)
"""
    with pytest.raises(AccessError):
        run_in_sandbox(src, plain)

    printed = run_in_sandbox(
        f"""
from moo.sdk import lookup
obj = lookup({target.pk})
print(obj)
""",
        plain,
    )
    assert "relation_hidden_object" not in "\n".join(printed)

    src = f"""
from moo.sdk import lookup
obj = lookup({target.pk})
list(obj.contents.all())
"""
    with pytest.raises(AccessError):
        run_in_sandbox(src, plain)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_verb_code_read_denial_blocks_source(t_init: Object, t_wizard: Object):
    """Verb.code must honor the verb's read ACL."""
    from moo.core.exceptions import AccessError
    from moo.sdk import create

    with ctx(t_wizard):
        target = create("relation_hidden_verb_object")
        target.add_verb("hidden_source", code='print("secret source")')
        plain = create("relation_hidden_verb_reader")
        verb = target.verbs.get(names__name="hidden_source")
        verb.deny(plain, "read")

    src = """
print(verb.code)
"""
    with pytest.raises(AccessError):
        run_in_sandbox(src, plain, extra_globals={"verb": verb})


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_parser_metadata_save_requires_wizard(t_init: Object, t_wizard: Object):
    """PrepositionSpecifier rows reachable from a Verb cannot be changed by non-wizards."""
    from moo.core.exceptions import AccessError
    from moo.sdk import create

    with ctx(t_wizard):
        target = create("relation_parser_metadata_object")
        target.add_verb("meta_test", code="return True", indirect_objects={"with": "any"})
        plain = create("relation_parser_metadata_reader")
        verb = target.verbs.get(names__name="meta_test")
        specifier = verb.indirect_objects.first()

    src = """
specifier.specifier = "none"
specifier.save()
"""
    with pytest.raises(AccessError):
        run_in_sandbox(src, plain, extra_globals={"specifier": specifier})

    specifier.refresh_from_db()
    assert specifier.specifier == "any"
