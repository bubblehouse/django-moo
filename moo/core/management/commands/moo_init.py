import importlib.resources
import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from moo.bootstrap import load_python
from moo.core.models import Repository

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Initialize a new database, or sync an existing one with --sync."

    def add_arguments(self, parser):
        parser.add_argument(
            "--bootstrap",
            type=str,
            default="default",
            help="Optionally pass a built-in template name or a Python source file to bootstrap the database.",
        )
        parser.add_argument(
            "--sync",
            action="store_true",
            default=False,
            help="Re-run the bootstrap script against an existing database to pick up new objects and verbs.",
        )
        parser.add_argument(
            "--hostname",
            default=None,
            help="Hostname of the Site to initialize (defaults to Site 1).",
        )

    def _find_bootstrap_path(self, bootstrap):
        """
        Locate the bootstrap.py entry-point for a named dataset under
        moo.bootstrap.  The script lives at
        ``moo/bootstrap/<name>/bootstrap.py`` so importing the package
        (for test discovery) does not run database-touching setup code.

        Resolves through ``moo.bootstrap.<name>`` directly so that datasets
        contributed by sibling distributions (e.g. ``moo-agent``'s ``zork1``
        package) are found via their own ``__path__``.
        """
        try:
            ref = importlib.resources.files(f"moo.bootstrap.{bootstrap}") / "bootstrap.py"
        except ModuleNotFoundError as exc:
            raise CommandError(
                f"Bootstrap '{bootstrap}' not found. Expected an entry point at moo/bootstrap/{bootstrap}/bootstrap.py."
            ) from exc
        try:
            with importlib.resources.as_file(ref) as path:
                if not path.exists():
                    raise CommandError(
                        f"Bootstrap '{bootstrap}' not found. "
                        f"Expected an entry point at moo/bootstrap/{bootstrap}/bootstrap.py."
                    )
                return path
        except (FileNotFoundError, TypeError) as exc:
            raise CommandError(
                f"Bootstrap '{bootstrap}' not found. Expected an entry point at moo/bootstrap/{bootstrap}/bootstrap.py."
            ) from exc

    def handle(self, *args, bootstrap="default", sync=False, hostname=None, **config):
        from django.contrib.sites.models import Site

        from moo.core.code import ContextManager
        from moo.core.managers import get_default_site

        if hostname:
            site, _ = Site.objects.get_or_create(domain=hostname, defaults={"name": hostname})
        else:
            site = get_default_site()
        ContextManager.set_site(site)

        with transaction.atomic():
            if sync:
                try:
                    Repository.objects.get(slug=bootstrap)
                except Repository.DoesNotExist as exc:
                    raise RuntimeError(
                        f"Dataset '{bootstrap}' has not been initialized. Run without --sync first."
                    ) from exc
                bootstrap_path = self._find_bootstrap_path(bootstrap)
                log.info("Syncing bootstrap '%s' against existing database...", bootstrap)
                load_python(bootstrap_path)
                log.info("Syncing complete for bootstrap '%s'.", bootstrap)
            else:
                try:
                    Repository.objects.get(slug=bootstrap)
                    raise RuntimeError("Looks like this database has already been initialized.")
                except Repository.DoesNotExist:
                    Repository.objects.create(
                        slug=bootstrap,
                        prefix=f"moo/bootstrap/{bootstrap}/verbs",
                        url=settings.DEFAULT_GIT_REPO_URL,
                    )
                bootstrap_path = self._find_bootstrap_path(bootstrap)
                load_python(bootstrap_path)
