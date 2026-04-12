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

    def _find_bootstrap_path(self, bootstrap):
        """
        Locate the __init__.py for a named bootstrap package under moo.bootstrap.
        Raises CommandError if not found.
        """
        ref = importlib.resources.files("moo.bootstrap") / bootstrap / "__init__.py"
        try:
            with importlib.resources.as_file(ref) as path:
                if not path.exists():
                    raise CommandError(
                        f"Bootstrap '{bootstrap}' not found. "
                        f"Expected a package at moo/bootstrap/{bootstrap}/__init__.py."
                    )
                return path
        except (FileNotFoundError, TypeError) as exc:
            raise CommandError(
                f"Bootstrap '{bootstrap}' not found. Expected a package at moo/bootstrap/{bootstrap}/__init__.py."
            ) from exc

    def handle(self, *args, bootstrap="default", sync=False, **config):
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
            else:
                try:
                    Repository.objects.get(slug=bootstrap)
                    raise RuntimeError("Looks like this database has already been initialized.")
                except Repository.DoesNotExist:
                    Repository.objects.create(
                        slug=bootstrap,
                        prefix=f"moo/bootstrap/{bootstrap}_verbs",
                        url=settings.DEFAULT_GIT_REPO_URL,
                    )
                bootstrap_path = self._find_bootstrap_path(bootstrap)
                load_python(bootstrap_path)
