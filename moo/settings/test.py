# -*- coding: utf-8 -*-
from .base import *  # pylint: disable=wildcard-import

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-061+p62f39ohlfrgu&)%1lxo%%#_-$rc5l_zsrlx6jqy)sw(=r"

DATABASES = {
    "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3", "TEST": {"NAME": ":memory:"}}
}
