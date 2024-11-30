# -*- coding: utf-8 -*-
"""
Support utilities for database boostrapping.
"""

import argparse
import shlex
import importlib.resources
import logging

parser = argparse.ArgumentParser('moo')
parser.add_argument('subcommand', choices=['verb'])
parser.add_argument('names', nargs='+')
parser.add_argument('--on', help='The object to add or modify the verb on')
parser.add_argument('--ability', action='store_true', help='Whether the verb is an intrinsic ability')
parser.add_argument('--method', action='store_true', help='Whether the verb is a method (callable from verb code)')

log = logging.getLogger(__name__)

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

def load_verbs(repo, dataset='default'):
    from moo.core.models.object import Object
    for ref in importlib.resources.files(f'moo.core.bootstrap.{dataset}_verbs').iterdir():
        if ref.name.startswith('_') or not ref.name.endswith('.py'):
            continue
        log.info(f"Loading verb source `{ref.name}`...")
        with ref.open() as f:
            contents = f.read()
            first, code = contents.split("\n", maxsplit=1)
            if first.startswith("#!moo "):
                args = parser.parse_args(shlex.split(first[6:]))
                obj = Object.objects.get(name=args.on)
                obj.add_verb(*args.names, code=code, filename=ref.name, repo=repo, ability=args.ability, method=args.method)
                
