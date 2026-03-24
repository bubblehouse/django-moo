import pytest

from django.contrib.auth.models import User  # pylint: disable=imported-auth-user
from simplesshkey.models import UserKey

from moo.core import code, parse
from moo.core.models import Object
from moo.core.exceptions import UserError, UsageError
from moo.sdk import lookup, list_ssh_keys

# A real Ed25519 public key used across tests.
TEST_ED25519_KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIENECd0+5MZVjAq4I1m1Am9zev/A309sk6dcxFiwnXEb test@example"


# --- @keys ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_keys_empty(t_init: Object, t_wizard: Object):
    """@keys prints 'No SSH keys configured.' when the player has no keys."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@keys")
    assert any("No SSH keys configured" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_keys_lists_added_key(t_init: Object, t_wizard: Object):
    """@keys shows numbered keys after one has been added."""
    user = User.objects.get(username="wizard")
    key = UserKey(user=user, key=TEST_ED25519_KEY)
    key.full_clean()
    key.save()

    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@keys")
    assert any("1." in line for line in printed)
    assert any("ssh-ed25519" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_keys_player_without_user(t_init: Object, t_wizard: Object):
    """@keys run as the Player NPC (no Django User) surfaces a clear error."""
    player_npc = lookup("Player")
    with code.ContextManager(t_wizard, lambda _: None):
        # Test the SDK function directly: the NPC has a Player record but user=None.
        with pytest.raises(UserError, match="no Django user account"):
            list_ssh_keys(player_npc)


# --- @add-key ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_add_key_valid(t_init: Object, t_wizard: Object):
    """@add-key with a valid public key creates a UserKey record."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, f"@add-key {TEST_ED25519_KEY}")
    user = User.objects.get(username="wizard")
    assert UserKey.objects.filter(user=user).count() == 1
    assert any("Added SSH key" in line for line in printed)
    assert any("ssh-ed25519" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_add_key_invalid(t_init: Object, t_wizard: Object):
    """@add-key with a malformed key string raises UserError and does not save."""
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        with pytest.raises(UserError, match="Invalid SSH key"):
            parse.interpret(ctx, "@add-key notavalidkey")
    user = User.objects.get(username="wizard")
    assert UserKey.objects.filter(user=user).count() == 0


# --- @remove-key ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_remove_key_valid(t_init: Object, t_wizard: Object):
    """@remove-key 1 deletes the first key and prints confirmation."""
    user = User.objects.get(username="wizard")
    key = UserKey(user=user, key=TEST_ED25519_KEY)
    key.full_clean()
    key.save()

    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@remove-key 1")
    assert UserKey.objects.filter(user=user).count() == 0
    assert any("Removed SSH key" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_remove_key_out_of_range(t_init: Object, t_wizard: Object):
    """@remove-key with an index beyond the list raises UserError."""
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        with pytest.raises(UserError, match="No key at index"):
            parse.interpret(ctx, "@remove-key 5")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_remove_key_non_integer(t_init: Object, t_wizard: Object):
    """@remove-key with a non-numeric argument raises UsageError."""
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        with pytest.raises(UsageError, match="not a valid index"):
            parse.interpret(ctx, "@remove-key abc")
