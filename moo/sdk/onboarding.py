# -*- coding: utf-8 -*-
"""
Guest tier and registration gate.

The onboarding funnel: a :func:`provision_guest` low-commitment entry that can
explore and talk but not build or own, and a :func:`register` step that binds a
durable identity (via a pluggable verifier) before an account is promoted past
guest into build rights.  Build-granting code gates on :func:`require_registered`.
"""

from django.conf import settings as _settings

from ..core.exceptions import UserError
from .context import context


# --- I: guest tier --------------------------------------------------------


def is_guest(account) -> bool:
    """True if an account is in the guest tier."""
    from ..core.models.auth import Player

    return account is not None and account.status == Player.STATUS_GUEST


def provision_guest(name, site=None, user=None):
    """Create a non-persistent guest avatar + account.

    The avatar is parented to ``$guest`` and given its own ``ownership_quota``
    of 0 so :func:`moo.sdk.create` refuses (the class default is not enough —
    ``create`` reads the quota with ``recurse=False``).

    :param name: display name for the guest avatar
    :param site: the Site to provision on (defaults to the active site)
    :param user: an optional Django User to tie the guest to (usually ``None``)
    :return: ``(account, avatar)``
    """
    from ..core.code import ContextManager
    from ..core.models.auth import Player
    from ..core.models.object import Object
    from .objects import lookup

    if site is None:
        site = ContextManager.get_site()

    guest_class = lookup("Generic Guest")
    # Object.save() forbids creating an object owned by anyone but the active
    # caller; create owned-by-caller, then self-own once it has a pk.
    caller = ContextManager.get("caller")
    avatar = Object.objects.create(name=name, owner=caller)
    avatar.owner = avatar
    avatar.save()
    avatar.parents.add(guest_class)
    # Own quota of 0 blocks creation (create() reads recurse=False).
    avatar.set_property("ownership_quota", 0)
    try:
        system = Object.objects.get(unique_name=True, name="System Object")
        start = system.get_property("player_start")
        if start is not None:
            avatar.location = start
            avatar.save()
    except Exception:  # pylint: disable=broad-except
        pass

    account = Player.objects.create(avatar=avatar, user=user, site=site, status=Player.STATUS_GUEST)
    return account, avatar


def remove_guest(account):
    """Reap a guest account and its avatar (the non-persistence side).

    No-op for a non-guest account, so it is safe to call unconditionally on
    disconnect.

    :param account: the guest Player account to remove
    :return: True if a guest was removed
    """
    if not is_guest(account):
        return False
    avatar = account.avatar
    account.delete()
    if avatar is not None:
        avatar.delete()
    return True


# --- J: registration gate -------------------------------------------------


def default_identity_verifier(identity):
    """The built-in durable-identity verifier.

    Loose by design — accepts any non-empty identity — so it is a working
    default; deployments point ``MOO_REGISTRATION_VERIFIER`` at a stricter one
    (email round-trip, SSO, etc.).

    .. warning::

       This default proves **nothing**: it normalizes the string but does not
       confirm the registrant controls the identity. Because a ban blacklists
       by identity (H), an unverified registration lets one user claim
       another's identifier. The ``(registered_identity, site)`` uniqueness
       constraint stops two accounts from holding the same identity, but only a
       real verifier stops a *first* false claim. Replace this before exposing
       ``@register`` on any deployment where bans must hold.

    :param identity: the candidate identifier
    :return: ``(ok, normalized, error)``
    """
    if not identity or not str(identity).strip():
        return False, None, "A non-empty identity is required."
    return True, str(identity).strip().lower(), None


def _load_verifier():
    """Resolve the configured registration verifier callable."""
    path = getattr(_settings, "MOO_REGISTRATION_VERIFIER", None)
    if not path:
        return default_identity_verifier
    from importlib import import_module

    module_path, _, attr = path.rpartition(".")
    return getattr(import_module(module_path), attr)


def register(account, identity):
    """Bind a durable identity to an account and promote it out of guest.

    Runs the pluggable verifier, refuses a banned identity (H), records the
    identity, and lifts a guest account to active.

    :param account: the Player account to register
    :param identity: the candidate durable identifier
    :raises UserError: on a missing account, a rejected identity, a banned one,
        or an identity already claimed on this site
    """
    from django.db import IntegrityError, transaction

    from ..core.models.auth import Player
    from .moderation import is_blacklisted

    if account is None:
        raise UserError("No account to register.")
    ok, normalized, error = _load_verifier()(identity)
    if not ok:
        raise UserError(error or "That identity could not be verified.")
    if is_blacklisted(normalized, account.site):
        raise UserError("That identity has been banned.")
    account.registered_identity = normalized
    if account.status == Player.STATUS_GUEST:
        account.status = Player.STATUS_ACTIVE
    try:
        # Savepoint so the (registered_identity, site) uniqueness violation
        # rolls back cleanly and leaves the surrounding transaction usable.
        with transaction.atomic():
            account.save()
    except IntegrityError as exc:
        raise UserError("That identity is already registered.") from exc
    return account


def require_registered(account):
    """Raise unless an account has bound a durable identity (the build gate).

    Build-granting code calls this so build rights require accountability.

    :param account: the Player account to check
    :raises UserError: if the account is unregistered
    """
    if account is None or not account.is_registered():
        raise UserError("You must register a durable identity before gaining build rights.")
    return True
