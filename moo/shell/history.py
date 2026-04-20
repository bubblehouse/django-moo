# -*- coding: utf-8 -*-
"""
Persistent per-player prompt history stored in the Django cache (Redis in prod).
"""

from prompt_toolkit.history import History


class RedisHistory(History):
    """
    prompt_toolkit History backed by the Django cache, scoped per Django user.

    Entries are stored as a list under ``moo:history:{user_pk}``, capped at ``cap``
    entries and refreshed with ``ttl`` seconds on every write so abandoned
    accounts eventually expire.
    """

    def __init__(self, user_pk: int, cap: int = 500, ttl: int = 90 * 86400):
        super().__init__()
        self.user_pk = user_pk
        self.cap = cap
        self.ttl = ttl
        self.key = f"moo:history:{user_pk}"

    def load_history_strings(self):
        from django.core.cache import cache

        entries = cache.get(self.key) or []
        for entry in reversed(entries):
            yield entry

    def store_string(self, string: str) -> None:
        if not string or not string.strip():
            return
        from django.core.cache import cache

        entries = cache.get(self.key) or []
        if entries and entries[-1] == string:
            return
        entries.append(string)
        if len(entries) > self.cap:
            entries = entries[-self.cap :]
        cache.set(self.key, entries, timeout=self.ttl)
