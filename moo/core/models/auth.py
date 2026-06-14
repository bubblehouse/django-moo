# -*- coding: utf-8 -*-
"""
Authentication support.
"""

from django.contrib.auth.models import User  # pylint: disable=imported-auth-user
from django.db import models
from django.db.models import Q
from django.utils import timezone

from .acl import WizardGuardedManager, require_wizard


class Player(models.Model):
    """The durable account record behind an avatar.

    A ``Player`` row is the first-class accountability anchor: its ``pk`` is a
    stable account id distinct from any avatar name, and moderation
    (provenance, gag, suspend, ban) keys to it rather than to a discardable
    avatar Object.  Today a row carries a single ``avatar``; the model is
    written so one account can later own several deliberately linked avatars
    without the safety set being retrofitted.
    """

    # Account lifecycle / moderation status. ``active`` and ``guest`` may log
    # in; ``suspended`` is reversible (cleared once ``suspended_until`` passes);
    # ``banned`` is terminal.  See :mod:`moo.sdk.moderation`.
    STATUS_ACTIVE = "active"
    STATUS_GUEST = "guest"
    STATUS_SUSPENDED = "suspended"
    STATUS_BANNED = "banned"
    STATUS_CHOICES = [(s, s) for s in (STATUS_ACTIVE, STATUS_GUEST, STATUS_SUSPENDED, STATUS_BANNED)]

    class Meta:
        constraints = [
            # Conditional: two anonymous (NULL user) Players are allowed; one user
            # cannot have two Players on the same site.
            models.UniqueConstraint(
                fields=["user", "site"],
                condition=Q(user__isnull=False),
                name="player_unique_user_per_site",
            ),
        ]
        indexes = [
            models.Index(fields=["avatar", "wizard"], name="player_avatar_wizard_idx"),
            models.Index(fields=["status"], name="player_status_idx"),
            models.Index(fields=["registered_identity"], name="player_identity_idx"),
        ]

    objects = WizardGuardedManager()

    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    avatar = models.ForeignKey("Object", null=True, on_delete=models.SET_NULL)
    wizard = models.BooleanField(default=False)
    site = models.ForeignKey("sites.Site", null=True, blank=True, on_delete=models.SET_NULL)

    # G — account model. A durable identity (email or another pluggable
    # verifier's id) bound at registration (J); moderation status (H); and the
    # reversible-suspend deadline.  ``registered_identity`` is what a ban
    # blacklists, so it outlives any single avatar.
    registered_identity = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    suspended_until = models.DateTimeField(null=True, blank=True)

    @property
    def account_id(self) -> int:
        """The stable account identifier (the row pk), distinct from any name."""
        return self.pk

    def is_registered(self) -> bool:
        """True once a durable identity has been bound (J)."""
        return bool(self.registered_identity)

    def is_suspended(self, now=None) -> bool:
        """True while a reversible suspension is in force.

        A suspension whose ``suspended_until`` has passed is treated as expired
        (callers should clear it on next login); an open-ended suspension
        (``status == suspended`` with no deadline) stays in force.
        """
        if self.status != self.STATUS_SUSPENDED:
            return False
        if self.suspended_until is None:
            return True
        return (now or timezone.now()) < self.suspended_until

    def login_blocked_reason(self, now=None):
        """Return a human-readable reason login is blocked, or ``None`` if allowed.

        The single chokepoint the SSH login path (H) consults so suspend/ban
        enforcement lives in one place.
        """
        if self.status == self.STATUS_BANNED:
            return "This account has been banned."
        if self.is_suspended(now):
            if self.suspended_until is not None:
                return f"This account is suspended until {self.suspended_until:%Y-%m-%d %H:%M UTC}."
            return "This account is suspended."
        return None

    def __str__(self):
        who = self.user.username if self.user else (self.avatar.name if self.avatar else "anonymous")
        return f"Player#{self.pk} ({who})"

    def save(self, *args, **kwargs):
        require_wizard("write", self)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        require_wizard("delete", self)
        return super().delete(*args, **kwargs)


class UniversalWizard(models.Model):
    """A user marked for cross-universe wizard rights.

    On SSH connection to any site, if the user has a UniversalWizard record
    and no Player exists for that ``(user, site)`` pair, a wizard avatar +
    Player is auto-provisioned for that site.

    This is the only mechanism that grants automatic cross-site wizard
    privileges; ``User.is_superuser`` alone does not.
    """

    objects = WizardGuardedManager()

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"UniversalWizard({self.user.username})"

    def save(self, *args, **kwargs):
        require_wizard("write", self)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        require_wizard("delete", self)
        return super().delete(*args, **kwargs)
