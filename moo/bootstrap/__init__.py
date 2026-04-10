# -*- coding: utf-8 -*-
"""
Support utilities for database boostrapping.
"""

import argparse
import importlib.resources
import logging
import shlex
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
parser.add_argument("--on", help="The object to add or modify the verb on", required=True)
parser.add_argument(
    "--dspec", "--dobj", choices=["this", "any", "none", "either"], default="none", help="The direct object specifier"
)
parser.add_argument(
    "--ispec", "--iobj", metavar="PREP:SPEC", nargs="+", help="Indirect object specifiers", action=ISpecAction
)


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
    ref = importlib.resources.files("moo.bootstrap") / f"{dataset}_verbs/{filename}"
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


def get_or_create_object(name, unique_name=False, parents=None, owner=None, location=None):
    """
    Get or create a named object. Safe to call on an already-bootstrapped database.

    :param name: The name of the object to get or create.
    :type name: str
    :param unique_name: Whether the object has a unique name constraint.
    :type unique_name: bool
    :param parents: A list of parent objects to add if the object is newly created.
    :type parents: list[Object] | None
    :param owner: The owner of the object.
    :type owner: Object | None
    :param location: The location of the object.
    :type location: Object | None
    :return: A ``(object, created)`` tuple.
    :rtype: tuple[Object, bool]
    """
    from moo.core.models import Object

    obj, created = Object.objects.get_or_create(
        name=name,
        unique_name=unique_name,
        defaults=dict(owner=owner, location=location),
    )
    if created and parents:
        for parent in parents:
            obj.parents.add(parent)
    return obj, created


def initialize_dataset(dataset="default"):
    """
    Initialize a new dataset, or sync an existing one.

    This will create the default objects and permissions for the dataset. Notably, it will
    create a `System Object` that is used to store global properties and verbs.

    It will also create a `Wizard` user that is used to manage the system.

    All operations are idempotent — safe to call on a DB that has already been initialized.

    :param dataset: The name of the dataset to initialize.
    :type dataset: str
    :return: The repository object for the dataset.
    :rtype: Repository
    """
    from moo.core import models
    from moo.core.parse import Pattern

    for name in settings.DEFAULT_PERMISSIONS:
        models.Permission.objects.get_or_create(name=name)
    Pattern.initializePrepositions()

    from django.contrib.auth.models import User  # pylint: disable=imported-auth-user
    from moo.core.models.auth import Player

    repo, _ = models.Repository.objects.get_or_create(
        slug=dataset,
        defaults=dict(
            prefix=f"moo/bootstrap/{dataset}_verbs",
            url=settings.DEFAULT_GIT_REPO_URL,
        ),
    )
    system, _ = models.Object.objects.get_or_create(name="System Object", unique_name=True)
    # LambdaMOO-style sentinel objects — created immediately after the system object
    # so they receive the lowest possible PKs (2, 3, 4).
    nothing, _ = models.Object.objects.get_or_create(name="nothing", unique_name=True)
    ambiguous_match, _ = models.Object.objects.get_or_create(name="ambiguous_match", unique_name=True)
    failed_match, _ = models.Object.objects.get_or_create(name="failed_match", unique_name=True)
    containers, containers_created = models.Object.objects.get_or_create(name="Generic Container", unique_name=True)
    if containers_created:
        containers.add_verb("accept", code="return True")
    # Create the first real user
    wizard, wizard_created = models.Object.objects.get_or_create(name="Wizard", unique_name=True)
    if wizard_created:
        wizard.add_verb("accept", code="return True")
    wizard.owner = wizard
    wizard.save()
    # Wizard gets a User and Player record so is_wizard() works
    user, _ = User.objects.get_or_create(username="wizard")
    Player.objects.get_or_create(user=user, defaults=dict(avatar=wizard, wizard=True))
    # Wizard owns the sentinel objects
    nothing.owner = wizard
    nothing.save()
    ambiguous_match.owner = wizard
    ambiguous_match.save()
    failed_match.owner = wizard
    failed_match.save()
    # Wizard owns containers
    containers.owner = wizard
    containers.save()
    # Wizard owns the system
    system.owner = wizard
    system.save()
    return repo


def parse_shebang(content):
    """
    Parse the ``#!moo verb`` shebang from verb source code.

    :param content: the full verb source code string
    :returns: ``(names, on, dspec, ispec)`` tuple if a valid shebang is present, else ``None``
    """
    try:
        first_line, _ = content.split("\n", maxsplit=1)
    except ValueError:
        return None
    if not first_line.startswith("#!moo verb"):
        return None
    shebang = first_line[6:]  # strip "#!moo "
    try:
        args = parser.parse_args(shlex.split(shebang))
    except SystemExit:
        return None
    ispec = args.ispec if hasattr(args, "ispec") else None
    return args.names, args.on, args.dspec, ispec


def load_verb_source(path, system, repo, replace=False):
    from moo.core.models.object import Object

    with open(path, encoding="utf8") as f:
        contents = f.read()
    result = parse_shebang(contents)
    if result is None:
        log.debug(f"Skipping verb source `{path.name}`...")
        return
    names, on, dspec, ispec = result
    log.debug(f"Loading verb source `{path.name}`...")
    if on.startswith("$"):
        obj = system.get_property(name=on[1:])
    else:
        obj = Object.objects.get(name=on)
    obj.add_verb(
        *names,
        code=contents,
        filename=str(path.resolve()),
        repo=repo,
        direct_object=dspec,
        indirect_objects=ispec,
        replace=replace,
    )


def load_verbs(repo, verb_package):
    """
    Load the verbs from a Python package into the database and associate them with the given repository.

    Verb files should start with a shebang:

    .. code-block::

            #!moo [-h] [--on ON] [--dspec {this,any,none,either}] [--ispec PREP:SPEC [PREP:SPEC ...]] {verb} names [names ...]

            positional arguments:
            {verb}
            names

            options:
            -h, --help            show this help message and exit
            --on ON               The object to add or modify the verb on
            --dspec {this,any,none,either}
                                    The direct object specifier
            --ispec PREP:SPEC [PREP:SPEC ...]
                                    Indirect object specifiers

    :param repo: The repository object for the dataset.
    :type repo: Repository
    :param verb_package: The Python package to load the verbs from.
    :type verb_package: str
    """
    from moo.core.models.object import Object

    system = Object.objects.get(pk=1)

    def _iterate_file_paths(ref):
        if ref.is_dir():
            for subref in ref.iterdir():
                _iterate_file_paths(subref)
        elif ref.is_file():
            with importlib.resources.as_file(ref) as path:
                if str(path).endswith(".py"):
                    load_verb_source(path, system, repo)

    for ref in importlib.resources.files(verb_package).iterdir():
        _iterate_file_paths(ref)
