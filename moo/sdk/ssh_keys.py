# -*- coding: utf-8 -*-
"""
SSH key management functions.
"""

from ..core.exceptions import UserError
from .context import context


def list_ssh_keys(player_obj):
    """
    Return a list of UserKey records for the player's Django User, ordered by creation date.

    :param player_obj: the player Object whose SSH keys to list
    :type player_obj: Object
    :return: list of UserKey model instances
    :rtype: list
    :raises UserError: if the caller is not wizard-owned, or the player has no account
    """
    from ..core.models.auth import Player
    from simplesshkey.models import UserKey

    if context.caller and not context.caller.is_wizard():
        raise UserError("Only verbs owned by wizards can manage SSH keys.")
    try:
        player_record = Player.objects.get(avatar=player_obj)
    except Player.DoesNotExist as exc:
        raise UserError(f"{player_obj.title()} has no player account.") from exc
    if player_record.user is None:
        raise UserError(f"{player_obj.title()} has no Django user account.")
    return list(UserKey.objects.filter(user=player_record.user).order_by("created"))


def add_ssh_key(player_obj, key_string):
    """
    Validate and add an SSH public key for the player's Django User.

    The key is parsed and normalised by simplesshkey before being saved.
    The key name is taken from the key's comment field if present.

    :param player_obj: the player Object to add the key to
    :type player_obj: Object
    :param key_string: the SSH public key string (e.g. ``ssh-rsa AAAA... comment``)
    :type key_string: str
    :return: the newly created UserKey instance
    :rtype: UserKey
    :raises UserError: if the caller is not wizard-owned, the key is invalid, or the player has no account
    """
    from ..core.models.auth import Player
    from simplesshkey.models import UserKey
    from django.core.exceptions import ValidationError

    if context.caller and not context.caller.is_wizard():
        raise UserError("Only verbs owned by wizards can manage SSH keys.")
    try:
        player_record = Player.objects.get(avatar=player_obj)
    except Player.DoesNotExist as exc:
        raise UserError(f"{player_obj.title()} has no player account.") from exc
    if player_record.user is None:
        raise UserError(f"{player_obj.title()} has no Django user account.")
    key = UserKey(user=player_record.user, key=key_string)
    try:
        key.full_clean()
    except ValidationError as e:
        raise UserError(f"Invalid SSH key: {e}") from e
    key.save()
    return key


def remove_ssh_key(player_obj, index):
    """
    Remove the SSH key at the given 1-based index for the player.

    The index corresponds to the position in the list returned by :func:`list_ssh_keys`.

    :param player_obj: the player Object whose SSH key to remove
    :type player_obj: Object
    :param index: 1-based position of the key to remove
    :type index: int
    :raises UserError: if the caller is not wizard-owned, the index is out of range, or the player has no account
    """
    from ..core.models.auth import Player
    from simplesshkey.models import UserKey

    if context.caller and not context.caller.is_wizard():
        raise UserError("Only verbs owned by wizards can manage SSH keys.")
    try:
        player_record = Player.objects.get(avatar=player_obj)
    except Player.DoesNotExist as exc:
        raise UserError(f"{player_obj.title()} has no player account.") from exc
    if player_record.user is None:
        raise UserError(f"{player_obj.title()} has no Django user account.")
    keys = list(UserKey.objects.filter(user=player_record.user).order_by("created"))
    if not (1 <= index <= len(keys)):
        raise UserError(f"No key at index {index}. Use @keys to list your keys.")
    key = keys[index - 1]
    key.delete()
    return key
