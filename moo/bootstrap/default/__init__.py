import importlib.resources
import logging
import secrets
from time import time

from django.contrib.auth import get_user_model
from moo import bootstrap
from moo.core import code, lookup
from moo.core.models import Player
from moo.core.models.acl import Access, Permission

log = logging.getLogger(__name__)
_repo = bootstrap.initialize_dataset("default")
wizard = lookup("Wizard")

_namespace = {
    "log": log,
    "secrets": secrets,
    "time": time,
    "User": get_user_model(),
    "bootstrap": bootstrap,
    "lookup": lookup,
    "Player": Player,
    "Access": Access,
    "Permission": Permission,
    "wizard": wizard,
    "repo": _repo,
}

_pkg = importlib.resources.files("moo.bootstrap") / "default"
_scripts = sorted(
    (f for f in _pkg.iterdir() if f.name.endswith(".py") and f.name[0].isdigit()),
    key=lambda f: f.name,
)

with code.ContextManager(wizard, log.info):
    for _script in _scripts:
        exec(compile(_script.read_text(encoding="utf8"), _script.name, "exec"), _namespace)  # pylint: disable=exec-used
