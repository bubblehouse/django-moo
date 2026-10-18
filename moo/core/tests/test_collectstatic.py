"""
collectstatic skips files by content, using a manifest kept in the storage.
"""

import hashlib
import io
import json
import os
import time

import pytest
from django.conf import settings as django_settings
from django.core.files.storage import FileSystemStorage
from django.core.management import call_command

from moo.core.management.commands.collectstatic import MANIFEST_NAME
from moo.storage import CachedS3Boto3Storage


class EtagFileSystemStorage(FileSystemStorage):
    """
    A local storage whose objects have ETags that change with their content, as S3's do.

    It reads its location from STATIC_ROOT: Django 5.0 rebuilds the staticfiles
    entry of an overridden STORAGES from the deprecated STATICFILES_STORAGE,
    which drops OPTIONS.
    """

    def __init__(self, **kwargs):
        super().__init__(location=django_settings.STATIC_ROOT, **kwargs)

    def list_etags(self):
        etags = {}
        for root, _dirs, files in os.walk(self.location):
            for filename in files:
                full = os.path.join(root, filename)
                with open(full, "rb") as handle:
                    etags[os.path.relpath(full, self.location)] = hashlib.md5(handle.read()).hexdigest()
        return etags


@pytest.fixture
def static(tmp_path, settings):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    (source / "a.css").write_text("a")
    (source / "b.css").write_text("b")
    settings.STATICFILES_DIRS = [str(source)]
    settings.STATICFILES_FINDERS = ["django.contrib.staticfiles.finders.FileSystemFinder"]
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": f"{__name__}.EtagFileSystemStorage"},
    }
    settings.STATIC_ROOT = str(target)
    return source, target


def collect():
    out = io.StringIO()
    call_command("collectstatic", interactive=False, verbosity=1, stdout=out)
    return out.getvalue()


def touch(*paths):
    later = time.time() + 3600
    for path in paths:
        os.utime(path, (later, later))


def test_first_run_copies_everything_and_writes_manifest(static):
    _source, target = static
    assert "2 static files copied" in collect()
    manifest = json.loads((target / MANIFEST_NAME).read_text())
    assert sorted(manifest) == ["a.css", "b.css"]
    assert manifest["a.css"]["sha256"] == hashlib.sha256(b"a").hexdigest()


def test_unchanged_files_skipped_despite_newer_mtimes(static):
    source, _target = static
    collect()
    touch(source / "a.css", source / "b.css")
    assert "0 static files copied" in collect()


def test_changed_content_is_copied(static):
    source, target = static
    collect()
    (source / "a.css").write_text("a2")
    touch(source / "a.css", source / "b.css")
    assert "1 static file copied" in collect()
    assert (target / "a.css").read_text() == "a2"


def test_object_changed_in_storage_is_copied(static):
    source, target = static
    collect()
    (target / "b.css").write_text("tampered")
    touch(source / "a.css", source / "b.css")
    assert "1 static file copied" in collect()
    assert (target / "b.css").read_text() == "b"


def test_object_deleted_from_storage_is_copied(static):
    source, target = static
    collect()
    (target / "a.css").unlink()
    touch(source / "a.css", source / "b.css")
    assert "1 static file copied" in collect()
    assert (target / "a.css").exists()


class FakeObject:
    def __init__(self, key, e_tag):
        self.key = key
        self.e_tag = e_tag


@pytest.mark.parametrize(
    "location, keys", [("", ["a.css", "admin/b.css"]), ("static", ["static/a.css", "static/admin/b.css"])]
)
def test_list_etags_names_objects_relative_to_location(monkeypatch, location, keys):
    prefixes = []

    class FakeObjects:
        def filter(self, Prefix):  # pylint: disable=invalid-name
            prefixes.append(Prefix)
            return [FakeObject(key, f'"{index}"') for index, key in enumerate(keys)]

    class FakeBucket:
        objects = FakeObjects()

    monkeypatch.setattr(CachedS3Boto3Storage, "bucket", property(lambda self: FakeBucket()))
    storage = CachedS3Boto3Storage(bucket_name="bucket", location=location)
    assert storage.list_etags() == {"a.css": '"0"', "admin/b.css": '"1"'}
    assert prefixes == [f"{location}/" if location else ""]
