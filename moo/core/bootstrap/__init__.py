# -*- coding: utf-8 -*-
"""
Support utilities for database boostrapping.
"""

import argparse
import importlib.resources
import logging
import shlex
import warnings

from django.conf import settings

log = logging.getLogger(__name__)


class ISpecAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):  # pylint: disable=redefined-outer-name
        """
        Custom action to handle the indirect object specifier.
        """
        values = values or []
        result = {}
        for value in values:
            if ":" not in value:
                raise argparse.ArgumentTypeError(f"Invalid indirect object specifier: {value}")
            preposition, specifier = value.split(":", 1)
            if specifier not in ["this", "any", "none"]:
                raise argparse.ArgumentTypeError(f"Invalid indirect object specifier: {specifier}")
            result[preposition] = specifier
        namespace.ispec = result
        return namespace


parser = argparse.ArgumentParser("moo")
parser.add_argument("subcommand", choices=["verb"])
parser.add_argument("names", nargs="+")
parser.add_argument("--on", help="The object to add or modify the verb on")
parser.add_argument("--dspec", choices=["this", "any", "none"], default="none", help="The direct object specifier")
parser.add_argument("--ispec", metavar="PREP:SPEC", nargs="+", help="Indirect object specifiers", action=ISpecAction)


def get_source(filename, dataset="default"):
    """
    Get the source code for a verb from a Python package.

    :param filename: The name of the file to get the source code for.
    :type filename: str
    :param dataset: The name of the dataset to get the source code for.
    :type dataset: str
    :return: The source code for the verb.
    :rtype: str
    """
    ref = importlib.resources.files("moo.core.bootstrap") / f"{dataset}_verbs/{filename}"
    with importlib.resources.as_file(ref) as path:
        with open(path, encoding="utf8") as f:
            return f.read()


def load_python(python_path):
    """
    Execute a provided Python bootstrap file against the provided database.

    :param python_path: The path to the Python file to execute.
    :type python_path: str
    """
    with open(python_path, encoding="utf8") as f:
        src = f.read()
        exec(compile(src, python_path, "exec"), globals(), dict())  # pylint: disable=exec-used


def initialize_dataset(dataset="default"):
    """
    Initialize a new dataset.

    This will create the default objects and permissions for the dataset. Notably, it will
    create a `System Object` that is used to store global properties and verbs.

    It will also create a `Wizard` user that is used to manage the system.

    :param dataset: The name of the dataset to initialize.
    :type dataset: str
    :return: The repository object for the dataset.
    :rtype: Repository
    """
    from moo.core import create, models
    from moo.core.parse import Pattern

    for name in settings.DEFAULT_PERMISSIONS:
        _ = models.Permission.objects.create(name=name)
    Pattern.initializePrepositions()

    repo = models.Repository.objects.get(slug=dataset)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        system = create(name="System Object", unique_name=True)
        set_default_permissions = models.Verb.objects.create(
            origin=system,
            repo=repo,
            code=get_source("_system_set_default_permissions.py", dataset=dataset),
        )
        set_default_permissions.names.add(
            models.VerbName.objects.create(verb=set_default_permissions, name="set_default_permissions")
        )
        set_default_permissions(set_default_permissions)
        set_default_permissions(system)
    containers = create(name="container class", unique_name=True)
    containers.add_verb("accept", code="return True")
    # Create the first real user
    wizard = create(name="Wizard", unique_name=True)
    wizard.add_verb("accept", code="return True")
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


def load_verbs(repo, verb_package):
    """
    Load the verbs from a Python package into the database and associate them with the given repository.

    Verb files should start with a shebang:

    .. code-block::

            #!moo [-h] [--on ON] [--ability] [--method] {verb} names [names ...]

            positional arguments:
            {verb}
            names

            options:
            -h, --help  show this help message and exit
            --on ON     The object to add or modify the verb on
            --ability   Whether the verb is an intrinsic ability
            --method    Whether the verb is a method (callable from verb code)

    :param repo: The repository object for the dataset.
    :type repo: Repository
    :param verb_package: The Python package to load the verbs from.
    :type verb_package: str
    """
    from moo.core.models.object import Object

    for ref in importlib.resources.files(verb_package).iterdir():
        if not ref.is_file():
            continue

        with importlib.resources.as_file(ref) as path:
            with open(path, encoding="utf8") as f:
                contents = f.read()
                try:
                    first, _ = contents.split("\n", maxsplit=1)
                except ValueError:
                    continue
                if first.startswith("#!moo "):
                    log.debug(f"Loading verb source `{ref.name}`...")
                    args = parser.parse_args(shlex.split(first[6:]))
                    obj = Object.objects.get(name=args.on)
                    obj.add_verb(
                        *args.names,
                        code=contents,
                        filename=str(path.resolve()),
                        repo=repo,
                        direct_object=args.dspec,
                        indirect_objects=args.ispec,
                    )
                else:
                    log.debug(f"Skipping verb source `{ref.name}`...")
