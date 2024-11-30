# -*- coding: utf-8 -*-
"""
Support utilities for database boostrapping.
"""

import argparse
import shlex
import importlib.resources
import logging
import warnings

from django.conf import settings

log = logging.getLogger(__name__)

parser = argparse.ArgumentParser('moo')
parser.add_argument('subcommand', choices=['verb'])
parser.add_argument('names', nargs='+')
parser.add_argument('--on', help='The object to add or modify the verb on')
parser.add_argument('--ability', action='store_true', help='Whether the verb is an intrinsic ability')
parser.add_argument('--method', action='store_true', help='Whether the verb is a method (callable from verb code)')

def get_source(filename, dataset='default'):
    ref = importlib.resources.files('moo.core.bootstrap') / f'{dataset}_verbs/{filename}'
    with importlib.resources.as_file(ref) as path:
        with open(path, encoding="utf8") as f:
            return f.read()

def load_python(python_path):
    """
    Execute a provided Python bootstrap file against the provided database.
    """
    with open(python_path, encoding="utf8") as f:
        src = f.read()
        exec(  # pylint: disable=exec-used
            compile(src, python_path, 'exec'), globals(), dict()
        )

def initialize_dataset(dataset='default'):
    from moo.core import create
    from moo.core import models
    for name in settings.DEFAULT_PERMISSIONS:
        _ = models.Permission.objects.create(name=name)
    repo = models.Repository.objects.get(slug=dataset)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', category=RuntimeWarning)
        system = create(name="System Object", unique_name=True)
        set_default_permissions = models.Verb.objects.create(
            method = True,
            origin = system,
            repo = repo,
            code = get_source('_system_set_default_permissions.py', dataset=dataset)
        )
        set_default_permissions.names.add(models.VerbName.objects.create(
            verb = set_default_permissions,
            name = 'set_default_permissions'
        ))
        set_default_permissions(set_default_permissions)
        set_default_permissions(system)
    containers = create(name="containers class", unique_name=True)
    containers.add_verb("accept", code="return True", method=True)
    # Create the first real user
    wizard = create(name="Wizard", unique_name=True, parents=[containers])
    wizard.owner = wizard
    wizard.save()
    # Wizard owns containers
    containers.owner = wizard
    containers.save()
    # Wizard owns the system...
    system.owner = wizard
    system.save()
    # ...and the default permissions verb
    set_default_permissions.owner = wizard
    set_default_permissions.save()
    return repo

def load_verbs(repo, dataset='default'):
    from moo.core.models.object import Object
    for ref in importlib.resources.files(f'moo.core.bootstrap.{dataset}_verbs').iterdir():
        if not ref.is_file():
            continue
        with ref.open() as f:
            contents = f.read()
            try:
                first, code = contents.split("\n", maxsplit=1)
            except ValueError:
                continue
            if first.startswith("#!moo "):
                log.info(f"Loading verb source `{ref.name}`...")
                args = parser.parse_args(shlex.split(first[6:]))
                obj = Object.objects.get(name=args.on)
                obj.add_verb(*args.names, code=code, filename=ref.name, repo=repo, ability=args.ability, method=args.method)
            else:
                log.info(f"Skipping verb source `{ref.name}`...")
