# -*- coding: utf-8 -*-
from .base import *  # pylint: disable=wildcard-import

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-06xo%2f39ohlfrgu&)%1lsrlx6jqy)s%#_-$rc5l_z1+p6w(=r"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["termiverse.dev.shacklyn.net", "probe.cluster.local"]
CSRF_TRUSTED_ORIGINS = ["https://moo.dev.shacklyn.net", "https://probe.cluster.local"]

# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "termiverse",
        "HOST": "termiverse-db.dev.shacklyn.net",
        "USER": "termiverse",
        "PASSWORD": "termiverse",
    }
}

# CACHES = {
#     'default': {
#         'BACKEND': 'redis_cache.RedisCache',
#         'LOCATION': 'redis:6379',
#     }
# }
