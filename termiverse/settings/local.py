# -*- coding: utf-8 -*-
from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-06xo%2f39ohlfrgu&)%1lsrlx6jqy)s%#_-$rc5l_z1+p6w(=r"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost']
CSRF_TRUSTED_ORIGINS = ['https://localhost']

# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

DATABASES = {
    'default': {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": "termiverse",
        "HOST": "postgres",
        "USER": "termiverse",
        "PASSWORD": "termiverse"
    }
}

STATIC_ROOT = "static"

# CACHES = {
#     'default': {
#         'BACKEND': 'redis_cache.RedisCache',
#         'LOCATION': 'redis:6379',
#     }
# }
