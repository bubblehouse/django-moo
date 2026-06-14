# -*- coding: utf-8 -*-
"""
Account-level identity helpers.

The :class:`~moo.core.models.auth.Player` row is the durable account behind an
avatar Object (its ``pk`` is the stable account id).  These helpers let verbs
and the safety set resolve from a discardable avatar to the account it belongs
to, and back, without each one re-deriving the relationship.  Multi-avatar
ownership is anticipated here: :func:`avatars_of` returns a list so that a
future "one account, several avatars" model needs no caller changes.
"""

from .context import context


def account_for(avatar_obj):
    """Return the :class:`Player` account for an avatar Object, or ``None``.

    :param avatar_obj: a player avatar Object
    :return: the owning Player account, or None if the object is not an avatar
    """
    from ..core.models.auth import Player

    if avatar_obj is None:
        return None
    return Player.objects.filter(avatar=avatar_obj).first()


def avatars_of(account):
    """Return the list of avatar Objects an account owns.

    Today an account carries a single avatar; this returns it as a one-element
    list (empty if the avatar has been recycled) so callers are already shaped
    for the later multi-avatar model.

    :param account: a Player account
    :return: list of avatar Objects
    """
    if account is None or account.avatar is None:
        return []
    return [account.avatar]


def account_id_for(avatar_obj):
    """Return the stable account id for an avatar, or ``None``.

    The cheap form used on the provenance hot path (E): one indexed lookup,
    no avatar materialization beyond the id.

    :param avatar_obj: a player avatar Object
    :return: the account pk, or None
    """
    from ..core.models.auth import Player

    if avatar_obj is None:
        return None
    return Player.objects.filter(avatar=avatar_obj).values_list("pk", flat=True).first()


def current_account():
    """Return the account for the current ``context.player``, or ``None``."""
    return account_for(context.player)
