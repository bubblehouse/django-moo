import pkg_resources as pkg

from django.core.management.base import BaseCommand
from django.conf import settings

from termiverse.core.bootstrap import load_python
from termiverse.core.models import Repository

builtin_templates = ['minimal', 'default']

class Command(BaseCommand):
    help = 'Initialize a new database.'

    def add_arguments(self, parser):
        parser.add_argument('--bootstrap', type=str, default='default',
            help="Optionally pass a built-in template name or a Python source file"
                 " to bootstrap the database.")

    def handle(self, bootstrap='default', *args, **config):
        try:
            repo = Repository.objects.get(slug='default')
            # raise RuntimeError("Looks like this database has already been initialized.")
        except Repository.DoesNotExist:
            repo = Repository(
                slug='default',
                prefix='termiverse/core/bootstrap/default_verbs',
                url=settings.DEFAULT_GIT_REPO_URL
            )
            repo.save()

        if(bootstrap in builtin_templates):
            bootstrap_path = pkg.resource_filename('termiverse.core.bootstrap', '%s.py' % bootstrap)
        else:
            bootstrap_path = bootstrap

        load_python(bootstrap_path)
