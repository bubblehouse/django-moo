# -*- coding: utf-8 -*-
"""
Append-only action audit log (spec 200, item L).

A trail of *consequential* actions — create, recycle/destroy, owner and
permission changes, and sanctions — keyed to the actor's durable account (G).
This is what moderation reports, transparent staff authority, and the reaper all
read from.  It is scoped tightly on purpose: only player-initiated consequential
actions are recorded, never every verb call, and bootstrap/system activity
(which has no human actor) is skipped entirely.
"""

from django.db import models


class AuditLog(models.Model):
    """One recorded consequential action."""

    CREATE = "create"
    RECYCLE = "recycle"
    DESTROY = "destroy"
    RESTORE = "restore"
    OWNER_CHANGE = "owner_change"
    PERMISSION_CHANGE = "permission_change"
    SUSPEND = "suspend"
    UNSUSPEND = "unsuspend"
    BAN = "ban"
    ACTION_CHOICES = [
        (a, a)
        for a in (
            CREATE,
            RECYCLE,
            DESTROY,
            RESTORE,
            OWNER_CHANGE,
            PERMISSION_CHANGE,
            SUSPEND,
            UNSUSPEND,
            BAN,
        )
    ]

    class Meta:
        indexes = [
            models.Index(fields=["-timestamp"], name="audit_timestamp_idx"),
            models.Index(fields=["actor", "-timestamp"], name="audit_actor_idx"),
            models.Index(fields=["action", "-timestamp"], name="audit_action_idx"),
        ]

    # The actor's account (G).  SET_NULL so deleting an account does not erase
    # the record of what it did.
    actor = models.ForeignKey("Player", null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=24, choices=ACTION_CHOICES)
    # The target is recorded by pk *and* a human-readable snapshot, so the row
    # stays meaningful even after the target is destroyed.
    target_id = models.IntegerField(null=True, blank=True)
    target_repr = models.CharField(max_length=255, blank=True, default="")
    detail = models.TextField(blank=True, default="")
    site = models.ForeignKey("sites.Site", null=True, blank=True, on_delete=models.SET_NULL)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        who = str(self.actor) if self.actor_id else "system"
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {who} {self.action} {self.target_repr}".strip()
