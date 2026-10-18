# -*- coding: utf-8 -*-
"""
collectstatic that skips files whose content is already in storage.
"""

import hashlib
import json

from django.contrib.staticfiles.management.commands import collectstatic
from django.core.files.base import ContentFile

MANIFEST_NAME = ".collectstatic-manifest.json"


def file_sha256(storage, path):
    """
    Return the SHA-256 hex digest of a file in a storage.
    """
    digest = hashlib.sha256()
    with storage.open(path) as handle:
        for chunk in handle.chunks():
            digest.update(chunk)
    return digest.hexdigest()


class Command(collectstatic.Command):
    """
    Skip a file by its content, not its modification time.

    Django skips a file only when the stored copy is newer than the source. Each
    image build gives every source file a new mtime, so every deploy uploaded all
    of them again. This version keeps a manifest in the storage of each file's
    SHA-256 and the ETag it was stored under. A file is skipped when its hash
    matches and the object still has that ETag.

    It applies only to a storage with list_etags(). INSTALLED_APPS lists moo.core
    above django.contrib.staticfiles so that this command replaces the stock one.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.known_hashes = {}
        self.source_hashes = {}

    def collect(self):
        if not hasattr(self.storage, "list_etags") or self.clear:
            return super().collect()
        etags = self.storage.list_etags()
        self.known_hashes = {
            name: entry["sha256"] for name, entry in self.read_manifest().items() if etags.get(name) == entry["etag"]
        }
        collected = super().collect()
        if not self.dry_run:
            self.write_manifest(self.storage.list_etags())
        return collected

    def delete_file(self, path, prefixed_path, source_storage):
        digest = file_sha256(source_storage, path)
        self.source_hashes[prefixed_path] = digest
        if self.known_hashes.get(prefixed_path) == digest:
            if prefixed_path not in self.unmodified_files:
                self.unmodified_files.append(prefixed_path)
            self.log(f"Skipping '{path}' (content unchanged)")
            return False
        return super().delete_file(path, prefixed_path, source_storage)

    def read_manifest(self):
        """
        Return the manifest left by the last run, or an empty one.
        """
        if not self.storage.exists(MANIFEST_NAME):
            return {}
        with self.storage.open(MANIFEST_NAME) as handle:
            try:
                return json.loads(handle.read())
            except ValueError:
                return {}

    def write_manifest(self, etags):
        """
        Record the hash and current ETag of every file collected in this run.
        """
        manifest = {
            name: {"sha256": digest, "etag": etags[name]}
            for name, digest in self.source_hashes.items()
            if name in etags
        }
        if self.storage.exists(MANIFEST_NAME):
            self.storage.delete(MANIFEST_NAME)
        self.storage.save(MANIFEST_NAME, ContentFile(json.dumps(manifest, sort_keys=True).encode()))
