# -*- coding: utf-8 -*-
"""
Staff sanction primitives.

The high rungs of the moderation ladder above ``@gag`` (self-defense) and
``@eject`` (room owner): a reversible :func:`suspend` (LambdaMOO's "newt", blocks
login for a period) and a scarring :func:`ban` (blacklists the account's durable
identity so it cannot simply re-register).  All key to the durable account (G),
none can target staff, and each is recorded to the audit log (L).  The login
path consults :func:`account_login_blocked` and :func:`is_blacklisted`.  A
:func:`mute` keeps the login but silences the account's speech.  Each sanction
calls ``on_sanction(kind)`` on the account's avatar, so a game can react.
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


def _notify_avatar(account, kind):
    """Schedule ``on_sanction(kind)`` on the account's avatar when it has the verb.

    The hook runs after the sanction commits, as its own task: it has its own
    time limit and transaction, so it can neither delay nor undo the sanction.
    The sanctioned avatar is the task's player, so code it owns never acts with
    the moderator's authority; the moderator stays the caller.
    """
    from django.db import transaction

    from .tasks import invoke

    avatar = account.avatar
    if avatar is None or not avatar.has_verb("on_sanction"):
        return
    verb = avatar.get_verb("on_sanction")
    moderator = context.caller
    transaction.on_commit(lambda: invoke(kind, verb=verb, _caller=moderator, _player=avatar))


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
    _notify_avatar(account, "suspend")
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
    _notify_avatar(account, "ban")
    return account


def mute(account, hours=None, reason=""):
    """Mute an account: it keeps its login, but its say, emote, page, and whisper reach no one.

    :param account: the Player account to mute
    :param hours: how long the mute lasts, more than 0; ``None`` is open-ended
    :param reason: optional free-text reason (recorded in the audit log)
    :raises PermissionError: if the caller is not staff
    :raises UserError: if the target is missing or is a staff account, or ``hours`` is not positive
    """
    import datetime

    from .audit import record_action

    _require_staff()
    _refuse_if_staff(account)
    if hours is not None and not 0 < float(hours) < 24 * 365 * 100:
        raise UserError("A mute needs a positive number of hours; use unmute to lift one.")
    # An open-ended mute runs until staff lift it; store a far deadline so one field holds both.
    span = datetime.timedelta(hours=float(hours)) if hours is not None else datetime.timedelta(days=365 * 100)
    account.muted_until = timezone.now() + span
    account.save(update_fields=["muted_until"])
    record_action("mute", target=account.avatar, detail=reason, force=True)
    _notify_avatar(account, "mute")
    return account


def unmute(account, reason=""):
    """Lift a mute.

    :param account: the Player account to unmute
    :raises PermissionError: if the caller is not staff
    :raises UserError: if the target is missing
    """
    from .audit import record_action

    _require_staff()
    if account is None:
        raise UserError("No such account.")
    account.muted_until = None
    account.save(update_fields=["muted_until"])
    record_action("unmute", target=account.avatar, detail=reason, force=True)
    return account


def is_muted(account) -> bool:
    """True while the account is muted. An account of ``None`` is never muted.

    :param account: the Player account, or ``None``
    """
    return account is not None and account.is_muted()


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
