# -*- coding: utf-8 -*-
"""
Moderation enforcement state.

A ban keys to the durable account (G), but an account-status flag alone leaks:
the offender re-registers under a new account.  :class:`Blacklist` is the
durable-identity / last-site denylist checked at login and registration so a
scarring ban actually holds.
"""

from django.db import models

from .acl import WizardGuardedManager, require_wizard


class Blacklist(models.Model):
    """A banned durable identity (and optionally the site it was banned on)."""

    class Meta:
        indexes = [
            models.Index(fields=["identity"], name="blacklist_identity_idx"),
        ]

    # Only staff sanctions write here; the guarded manager + save/delete keep a
    # non-wizard from minting or lifting a ban out from under moderation.
    objects = WizardGuardedManager()

    identity = models.CharField(max_length=255)
    site = models.ForeignKey("sites.Site", null=True, blank=True, on_delete=models.SET_NULL)
    reason = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        require_wizard("write", self)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        require_wizard("delete", self)
        return super().delete(*args, **kwargs)

    def __str__(self):
        return f"Blacklist({self.identity})"
