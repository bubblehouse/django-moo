import logging
import warnings

from django.conf import settings

from moo.core import models, bootstrap, code
from moo.core import create

log = logging.getLogger(__name__)

for name in settings.DEFAULT_PERMISSIONS:
    p = models.Permission.objects.create(name=name)

repo = models.Repository.objects.get(slug='test')
with warnings.catch_warnings():
    warnings.simplefilter('ignore', category=RuntimeWarning)
    system = create(name="System Object", unique_name=True)
    set_default_permissions = models.Verb.objects.create(
        method = True,
        origin = system,
        repo = repo,
        code = bootstrap.get_source('system_set_default_permissions.py', dataset='test')
    )
    set_default_permissions.names.add(models.VerbName.objects.create(
        verb = set_default_permissions,
        name = 'set_default_permissions'
    ))
    set_default_permissions(set_default_permissions)
    set_default_permissions(system)

# Create the first real user
wizard = create(name="Wizard", unique_name=True)
wizard.owner = wizard
wizard.save()
# Wizard owns the system...
system.owner = wizard
system.save()
# ...and the default permissions verb
set_default_permissions.owner = wizard
set_default_permissions.save()

with code.context(wizard, log.info):
    bag = create('bag of holding', location=wizard)
    hammer = create('wizard hammer', location=bag)
    book = create('class book', location=bag)
    players = create('player class', location=book)
    players.add_verb("look", "inspect", filename="players_look.py", repo=repo, ability=True, method=True)
    wizard.add_verb("test-args", filename="players_test_args.py", repo=repo, ability=True, method=True)
    wizard.add_verb("test-nested-verbs", filename="players_test_nested_verbs.py", repo=repo, ability=True, method=True)
    wizard.add_verb("test-async-verbs", filename="players_test_async_verbs.py", repo=repo, ability=True, method=True)
    guests = create('guest class', location=book)
    guests.parents.add(players)
    authors = create('author class', location=book)
    authors.parents.add(players)
    programmers = create('programmer class', location=book)
    programmers.parents.add(authors)
    wizards = create('wizard class', location=book)
    wizards.parents.add(programmers)

    wizard.parents.add(wizards)

    rooms = create('room class', location=book)
    rooms.set_property("description", "There's not much to see here.", inherited=True)

    lab = create('The Laboratory')
    lab.parents.add(rooms)
    lab.set_property("description", """A cavernous laboratory filled with gadgetry of every kind,
    this seems like a dumping ground for every piece of dusty forgotten
    equipment a mad scientist might require.""")

    wizard.location = lab
    wizard.save()

    player = create(name="Player", unique_name=True, location=lab)
    player.parents.add(players)
