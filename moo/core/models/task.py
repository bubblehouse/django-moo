# -*- coding: utf-8 -*-
"""
Task model.
"""

from django.db import models


class Task(models.Model):
    user = models.ForeignKey("Object", related_name="tasks", on_delete=models.CASCADE)
    origin = models.ForeignKey("Object", related_name="+", on_delete=models.CASCADE)
    verb_name = models.CharField(max_length=255)
    args = models.TextField()
    kwargs = models.TextField()
    created = models.DateTimeField()
    delay = models.IntegerField()
    killed = models.BooleanField(default=False)
    error = models.CharField(max_length=255, blank=True, null=True)
    trace = models.TextField(blank=True, null=True)
