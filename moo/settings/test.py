# -*- coding: utf-8 -*-
import os

from .base import *  # pylint: disable=wildcard-import

os.environ.setdefault("CELERY_RESULT_BACKEND", "django-db")

INSTALLED_APPS += ["django_celery_results"]  # noqa: F405

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-061+p62f39ohlfrgu&)%1lxo%%#_-$rc5l_zsrlx6jqy)sw(=r"

DATABASES = {
    "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3", "TEST": {"NAME": ":memory:"}}
}

# All tests that move objects around while having enterfuncs and exitfuncs
# need to run tasks eagerly to ensure that the enterfuncs and exitfuncs are
# executed within the same test transaction.
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# Disable cross-session attribute cache in tests: the in-process LocMemCache
# does not reset between test cases, which would poison subsequent tests
# when PKs are reused after sequence resets.
MOO_ATTRIB_CACHE_TTL = 0
