# -*- coding: utf-8 -*-
"""
Staff sanction primitives.

The high rungs of the moderation ladder above ``@gag`` (self-defense) and
``@eject`` (room owner): a reversible :func:`suspend` (LambdaMOO's "newt", blocks
login for a period) and a scarring :func:`ban` (blacklists the account's durable
identity so it cannot simply re-register).  All key to the durable account (G),
none can target staff, and each is recorded to the audit log (L).  The login
path consults :func:`account_login_blocked` and :func:`is_blacklisted`.
"""

from django.utils import timezone

from ..core.exceptions import UserError, AccessError
from .context import context


def _require_staff():
    """Raise unless the current caller is a wizard (or there is no caller)."""
    caller = context.caller
    if caller is not None and not caller.is_wizard():
        raise AccessError(caller, "sanction", "account")


def _refuse_if_staff(account):
    """Sanctions cannot target a staff account."""
    if account is None:
        raise UserError("No such account.")
    if account.wizard:
        raise UserError("Staff accounts cannot be sanctioned.")


def suspend(account, duration=None, hours=None, reason=""):
    """Suspend an account, blocking login until the deadline elapses.

    :param account: the Player account to suspend
    :param duration: a ``datetime.timedelta``, or ``None`` for open-ended
    :param hours: convenience for verb authors (who cannot import ``datetime``
        in the sandbox); converted to a ``duration``. Ignored if ``duration``
        is given.
    :param reason: optional free-text reason (recorded in the audit log)
    :raises PermissionError: if the caller is not staff
    :raises UserError: if the target is missing or is a staff account
    """
    import datetime

    from ..core.models.auth import Player  # noqa: F401
    from .audit import record_action

    _require_staff()
    _refuse_if_staff(account)
    if duration is None and hours is not None:
        # ``hours=0`` is an immediate (already-expired) suspension, not the
        # open-ended one a falsy ``and hours`` check would have produced.
        duration = datetime.timedelta(hours=float(hours))
    account.status = Player.STATUS_SUSPENDED
    account.suspended_until = (timezone.now() + duration) if duration is not None else None
    account.save()
    record_action("suspend", target=account.avatar, detail=reason, force=True)
    return account


def unsuspend(account, reason=""):
    """Lift a suspension, returning the account to active.

    :param account: the Player account to reinstate
    :raises PermissionError: if the caller is not staff
    """
    from ..core.models.auth import Player
    from .audit import record_action

    _require_staff()
    if account is None:
        raise UserError("No such account.")
    account.status = Player.STATUS_ACTIVE
    account.suspended_until = None
    account.save()
    record_action("unsuspend", target=account.avatar, detail=reason, force=True)
    return account


def ban(account, reason=""):
    """Ban an account and blacklist its durable identity / last site.

    The status flag stops this account; the :class:`Blacklist` row stops the
    same human from re-registering under a fresh account.

    :param account: the Player account to ban
    :raises PermissionError: if the caller is not staff
    :raises UserError: if the target is missing or is a staff account
    """
    from ..core.models.auth import Player
    from ..core.models.moderation import Blacklist
    from .audit import record_action

    _require_staff()
    _refuse_if_staff(account)
    account.status = Player.STATUS_BANNED
    account.save()
    if account.registered_identity:
        Blacklist.objects.create(
            identity=account.registered_identity,
            site=account.site,
            reason=reason,
        )
    record_action("ban", target=account.avatar, detail=reason, force=True)
    return account


def is_blacklisted(identity, site=None) -> bool:
    """True if a durable identity is banned (globally, or on the given site).

    :param identity: the durable identifier to check
    :param site: optional Site to scope the check to
    """
    from ..core.models.moderation import Blacklist

    if not identity:
        return False
    qs = Blacklist.objects.filter(identity=identity)
    if qs.filter(site__isnull=True).exists():
        return True
    if site is not None and qs.filter(site=site).exists():
        return True
    return qs.exists()


def account_login_blocked(account):
    """Return a reason string if this account may not log in, else ``None``.

    The single chokepoint the SSH login path consults — composes the account's
    own status (suspended/banned) with the identity blacklist.

    :param account: the Player account attempting to log in
    """
    from ..core.models.auth import Player

    if account is None:
        return None
    reason = account.login_blocked_reason()
    if reason:
        return reason
    # Login is allowed — but if a suspension has lapsed, clear the stale flag so
    # the account does not read as "suspended" forever in staff reports. Runs at
    # the login chokepoint, where there is no active caller, so the guarded
    # ``save()`` is permitted.
    if account.status == Player.STATUS_SUSPENDED and not account.is_suspended():
        account.status = Player.STATUS_ACTIVE
        account.suspended_until = None
        account.save()
    if account.registered_identity and is_blacklisted(account.registered_identity, account.site):
        return "This identity has been banned."
    return None
