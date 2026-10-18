# -*- coding: utf-8 -*-
from django.utils.functional import cached_property
from django.utils.module_loading import import_string
from storages.backends.s3boto3 import S3Boto3Storage


class CachedS3Boto3Storage(S3Boto3Storage):  # pylint: disable=abstract-method
    """
    S3 storage backend that saves the files locally, too.
    """

    @cached_property
    def local_storage(self):
        # Built on first save, not with the storage: compressor reads its
        # settings on import, and needs a STATIC_ROOT only some settings define.
        return import_string("compressor.storage.CompressorFileStorage")()

    def save(self, name, content):  # pylint: disable=arguments-differ
        self.local_storage._save(name, content)  # pylint: disable=protected-access
        super().save(name, self.local_storage._open(name))  # pylint: disable=protected-access
        return name

    def list_etags(self):
        """
        Return the ETag of every object under this storage's location, by name.

        One paginated listing, so the cost does not grow with a request per file.
        With SSE-KMS an ETag is not an MD5 of the content; it only changes when
        the object does.
        """
        prefix = f"{self.location}/" if self.location else ""  # pylint: disable=no-member
        return {obj.key[len(prefix) :]: obj.e_tag for obj in self.bucket.objects.filter(Prefix=prefix)}
