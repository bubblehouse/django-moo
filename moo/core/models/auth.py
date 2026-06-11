# -*- coding: utf-8 -*-
"""
Authentication support.
"""

from django.contrib.auth.models import User  # pylint: disable=imported-auth-user
from django.db import models
from django.db.models import Q

from .acl import WizardGuardedManager, require_wizard


class Player(models.Model):
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
        ]

    objects = WizardGuardedManager()

    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    avatar = models.ForeignKey("Object", null=True, on_delete=models.SET_NULL)
    wizard = models.BooleanField(default=False)
    site = models.ForeignKey("sites.Site", null=True, blank=True, on_delete=models.SET_NULL)

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
