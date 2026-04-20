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

    candidates = [p for p in Player.objects.filter(avatar=player_obj) if p.user is not None]
    if not candidates:
        raise UserError(f"{player_obj.title()} has no Django user account.")

    if old_password is not None:
        matched = [p for p in candidates if p.user.check_password(old_password)]
        if not matched:
            raise UserError("Incorrect old password.")
        user = matched[0].user
    else:
        if len(candidates) > 1:
            raise UserError(
                f"{player_obj.title()} has multiple user accounts; "
                "old password is required to select which one to change."
            )
        user = candidates[0].user

    try:
        validate_password(new_password, user=user)
    except ValidationError as e:
        raise UserError(f"Password rejected: {'; '.join(e.messages)}") from e

    user.set_password(new_password)
    user.save()
