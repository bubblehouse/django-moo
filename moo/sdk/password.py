# -*- coding: utf-8 -*-
"""
Password management functions.
"""


def set_password(player_obj, new_password, old_password=None):
    """
    Set the Django User password for a MOO player object.

    Non-wizard players must supply old_password for identity verification.
    Wizard players may omit old_password to perform an administrative reset.

    :param player_obj: the player Object whose password to change
    :param new_password: the new plaintext password to set
    :param old_password: the current password (required for non-wizard players)
    :raises UserError: bad old password, no account, or validation failure
    """
    from django.contrib.auth.password_validation import validate_password  # pylint: disable=import-outside-toplevel
    from django.core.exceptions import ValidationError  # pylint: disable=import-outside-toplevel
    from ..core.exceptions import UserError  # pylint: disable=import-outside-toplevel
    from .context import context  # pylint: disable=import-outside-toplevel
    from ..core.models.auth import Player  # pylint: disable=import-outside-toplevel

    if context.caller and not context.caller.is_wizard():
        raise UserError("Only verbs owned by wizards can change passwords.")
    if context.player and not context.player.is_wizard() and player_obj != context.player:
        raise UserError("You can only change your own password.")

    try:
        player_record = Player.objects.get(avatar=player_obj)
    except Player.DoesNotExist as exc:
        raise UserError(f"{player_obj.title()} has no player account.") from exc
    if player_record.user is None:
        raise UserError(f"{player_obj.title()} has no Django user account.")

    user = player_record.user

    if old_password is not None and not user.check_password(old_password):
        raise UserError("Incorrect old password.")

    try:
        validate_password(new_password, user=user)
    except ValidationError as e:
        raise UserError(f"Password rejected: {'; '.join(e.messages)}") from e

    user.set_password(new_password)
    user.save()
