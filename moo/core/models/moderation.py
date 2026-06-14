# -*- coding: utf-8 -*-
"""
Moderation enforcement state (spec 200, item H).

A ban keys to the durable account (G), but an account-status flag alone leaks:
the offender re-registers under a new account.  :class:`Blacklist` is the
durable-identity / last-site denylist checked at login and registration so a
scarring ban actually holds.
"""

from django.db import models


class Blacklist(models.Model):
    """A banned durable identity (and optionally the site it was banned on)."""

    class Meta:
        indexes = [
            models.Index(fields=["identity"], name="blacklist_identity_idx"),
        ]

    identity = models.CharField(max_length=255)
    site = models.ForeignKey("sites.Site", null=True, blank=True, on_delete=models.SET_NULL)
    reason = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Blacklist({self.identity})"
