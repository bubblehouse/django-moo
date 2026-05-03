from django.apps import AppConfig


class BootstrapConfig(AppConfig):
    """App config for ``moo.bootstrap``.

    Intentionally enabled only in ``moo.settings.test`` so the seed
    migration that loads the ``default`` dataset runs against test
    databases. Production initialization runs through ``manage.py
    moo_init`` / ``moo_init --sync``; adding this app to base/dev/local
    settings would cause the seed migration to run against a real DB.
    """

    name = "moo.bootstrap"
    verbose_name = "MOO Bootstrap"
