# -*- coding: utf-8 -*-
"""
Action audit log helpers (spec 200, item L).

:func:`record_action` is the single write point for the append-only
:class:`~moo.core.models.audit.AuditLog`.  Core paths (create, recycle,
sanction) call it; it resolves the actor from the current account (G) and skips
anything with no human actor, so bootstrap and system activity never floods the
log.  :func:`query_audit` is the staff-only read side.
"""

from .context import context


def record_action(action, target=None, detail="", actor=None, force=False):
    """Append one consequential action to the audit log.

    :param action: one of :class:`~moo.core.models.audit.AuditLog`'s action
        constants
    :param target: the affected Object (or ``None``); recorded by pk and a
        name snapshot so the row survives the target's deletion
    :param detail: optional free-text / serialized context
    :param actor: the acting Player account; defaults to the current account
    :param force: record even when no human actor is resolvable (used by
        staff-initiated sanctions that must always be logged)
    :return: the created AuditLog row, or ``None`` if skipped
    """
    from ..core.code import ContextManager
    from ..core.models import AuditLog
    from .accounts import account_for

    if actor is None:
        actor = account_for(context.player)
    # Consequential = player-initiated. Skip system/bootstrap noise unless the
    # caller explicitly forces the record (e.g. an account-targeted sanction).
    if actor is None and not force:
        return None

    target_id = getattr(target, "pk", None)
    target_repr = ""
    if target is not None:
        name = getattr(target, "name", None)
        target_repr = f"#{target_id} ({name})" if name else f"#{target_id}"

    return AuditLog.objects.create(
        actor=actor,
        action=action,
        target_id=target_id,
        target_repr=target_repr[:255],
        detail=str(detail)[:10000],
        site=ContextManager.get_site(),
    )


def query_audit(actor=None, action=None, target=None, limit=50):
    """Return recent audit rows, most recent first (staff-only at the verb layer).

    :param actor: filter to a Player account
    :param action: filter to one action kind
    :param target: filter to an affected Object (by pk)
    :param limit: maximum rows to return
    :return: list of AuditLog rows
    """
    from ..core.models import AuditLog

    qs = AuditLog.objects.all()
    if actor is not None:
        qs = qs.filter(actor=actor)
    if action is not None:
        qs = qs.filter(action=action)
    if target is not None:
        qs = qs.filter(target_id=getattr(target, "pk", target))
    return list(qs.order_by("-timestamp", "-id")[:limit])
