# -*- coding: utf-8 -*-
"""
Authentication support.
"""

from django.contrib.auth.models import \
    User  # pylint: disable=imported-auth-user
from django.db import models


class Player(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=["avatar", "wizard"], name="player_avatar_wizard_idx"),
        ]

    user = models.OneToOneField(User, null=True, on_delete=models.CASCADE)
    avatar = models.ForeignKey("Object", null=True, on_delete=models.SET_NULL)
    wizard = models.BooleanField(default=False)
