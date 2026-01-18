# -*- coding: utf-8 -*-
from .base import *  # pylint: disable=wildcard-import

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-061+p62f39ohlfrgu&)%1lxo%%#_-$rc5l_zsrlx6jqy)sw(=r"

DATABASES = {
    "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3", "TEST": {"NAME": ":memory:"}}
}

# All tests that move objects around while having enterfuncs and exitfuncs
# need to run tasks eagerly to ensure that the enterfuncs and exitfuncs are
# executed within the same test transaction.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_STORE_EAGER_RESULT = True
