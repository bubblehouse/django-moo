import importlib.resources
import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from moo.bootstrap import load_python
from moo.core.models import Repository

log = logging.getLogger(__name__)

builtin_templates = ["minimal", "default"]


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

    def handle(self, *args, bootstrap="default", sync=False, **config):
        with transaction.atomic():
            if sync:
                try:
                    Repository.objects.get(slug=bootstrap)
                except Repository.DoesNotExist as exc:
                    raise RuntimeError(
                        f"Dataset '{bootstrap}' has not been initialized. Run without --sync first."
                    ) from exc
                if bootstrap not in builtin_templates:
                    raise NotImplementedError(bootstrap)
                ref = importlib.resources.files("moo.bootstrap") / bootstrap / "__init__.py"
                with importlib.resources.as_file(ref) as path:
                    bootstrap_path = path
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
                if bootstrap in builtin_templates:
                    ref = importlib.resources.files("moo.bootstrap") / bootstrap / "__init__.py"
                    with importlib.resources.as_file(ref) as path:
                        bootstrap_path = path
                else:
                    raise NotImplementedError(bootstrap)
                load_python(bootstrap_path)
