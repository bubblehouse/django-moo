# -*- coding: utf-8 -*-
from django.core.files.storage import get_storage_class
from storages.backends.s3boto3 import S3Boto3Storage


class CachedS3Boto3Storage(S3Boto3Storage):  # pylint: disable=abstract-method
    """
    S3 storage backend that saves the files locally, too.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.local_storage = get_storage_class("compressor.storage.CompressorFileStorage")()

    def save(self, name, content):  # pylint: disable=arguments-differ
        self.local_storage._save(name, content)  # pylint: disable=protected-access
        super().save(name, self.local_storage._open(name))  # pylint: disable=protected-access
        return name
