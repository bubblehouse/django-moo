# -*- coding: utf-8 -*-
from .base import *  # pylint: disable=wildcard-import

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-061+p62f39ohlfrgu&)%1lxo%%#_-$rc5l_zsrlx6jqy)sw(=r"

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_STORE_EAGER_RESULT = True
