# -*- coding: utf-8 -*-
from .base import *  # pylint: disable=wildcard-import

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-06xo%2f39ohlfrgu&)%1lsrlx6jqy)s%#_-$rc5l_z1+p6w(=r"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["localhost"]
CSRF_TRUSTED_ORIGINS = ["https://localhost"]
STATIC_ROOT = "static"

# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "moo",
        "HOST": "postgres",
        "USER": "moo",
        "PASSWORD": "moo",
    }
}

# Cache
# https://docs.djangoproject.com/en/4.2/ref/settings/#caches

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "rediss://redis:6379",
    }
}

# Celery configuration
# https://docs.celeryq.dev/en/stable/userguide/configuration.html

CELERY_BROKER_URL = "redis://redis:6379/0"
