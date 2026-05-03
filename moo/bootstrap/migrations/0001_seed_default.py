"""Seed the ``default`` dataset into the test database.

Runs only when ``moo.bootstrap`` is in ``INSTALLED_APPS`` (test settings
only). Captured by pytest-django's snapshot serialization the same way
content-types are, so transactional tests with
``serialized_rollback=True`` restore the post-bootstrap state without
needing to re-run ``load_python`` per test.
"""

import importlib.resources

from django.db import migrations


def forward(apps, schema_editor):  # pylint: disable=unused-argument
    # Live-model imports are intentional: by the time this migration runs
    # the schema is fully built (we depend on the latest core/sites/auth
    # migrations) and the bootstrap script itself uses live models to add
    # verbs.
    from moo.bootstrap import load_python  # pylint: disable=import-outside-toplevel

    pkg = importlib.resources.files("moo.bootstrap")
    ref = pkg / "default" / "bootstrap.py"
    with importlib.resources.as_file(ref) as path:
        load_python(path)


def backward(apps, schema_editor):  # pylint: disable=unused-argument
    # Test DBs are dropped wholesale; no reverse needed.
    pass


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("core", "0031_universal_wizard"),
        ("sites", "0002_alter_domain_unique"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]
    operations = [migrations.RunPython(forward, backward)]
