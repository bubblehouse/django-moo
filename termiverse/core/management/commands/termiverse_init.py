import importlib.resources

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
            Repository.objects.get(slug=bootstrap)
            raise RuntimeError("Looks like this database has already been initialized.")
        except Repository.DoesNotExist:
            Repository.objects.create(
                slug=bootstrap,
                prefix=f'termiverse/core/bootstrap/{bootstrap}_verbs',
                url=settings.DEFAULT_GIT_REPO_URL
            )
        if(bootstrap in builtin_templates):
            ref = importlib.resources.files('termiverse.core.bootstrap') / f'{bootstrap}.py'
            with importlib.resources.as_file(ref) as path:
                bootstrap_path = path
        else:
            raise NotImplementedError(bootstrap)
        load_python(bootstrap_path)
