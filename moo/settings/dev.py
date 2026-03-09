# -*- coding: utf-8 -*-
import os

from .base import *  # pylint: disable=wildcard-import

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-06xo%2f39ohlfrgu&)%1lsrlx6jqy)s%#_-$rc5l_z1+p6w(=r"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["moo.dev.shacklyn.net", "probe.cluster.local"]
CSRF_TRUSTED_ORIGINS = ["https://moo.dev.shacklyn.net", "https://probe.cluster.local"]

DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
STATICFILES_STORAGE = 'moo.storage.CachedS3Boto3Storage'
AWS_STORAGE_BUCKET_NAME = 'django-moo-dev-assets-386413725601-us-east-2'
AWS_S3_ADDRESSING_STYLE = "virtual"

STATIC_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/"
STATIC_ROOT = '/usr/app/static'

COMPRESS_ENABLED = True
COMPRESS_ROOT = STATIC_ROOT
COMPRESS_STORAGE = STATICFILES_STORAGE
COMPRESS_URL = STATIC_URL

# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "moo",
        "HOST": "krustylu-db.dev.shacklyn.net",
        # "HOST": "bubblehouse-dev-moo-db.cluster-cbepmog7ejmj.us-east-2.rds.amazonaws.com",
        "USER": "moo",
        "PASSWORD": os.getenv("DB_PASSWORD", "moo"),
        "CONN_MAX_AGE": 60,
    }
}
MOO_BATCH_VERB_DISPATCH = True

REDIS_HOSTNAME = os.environ.get("REDIS_HOSTNAME", "redis")
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': f'redis://{REDIS_HOSTNAME}:6379',
    }
}
