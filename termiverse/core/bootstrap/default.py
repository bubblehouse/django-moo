import logging

from django.conf import settings

from termiverse.core import models, bootstrap, code
from termiverse.core.models.object import create_object

log = logging.getLogger(__name__)

for name in settings.DEFAULT_PERMISSIONS:
    p = models.Permission.objects.create(name=name)

repo = models.Repository.objects.get(slug='default')
system = create_object(name="System Object", unique_name=True)

# Configure `set_default_permissions` the long way
set_default_permissions = models.Verb.objects.create(
    method = True,
    origin = system,
    repo = repo,
    code = bootstrap.get_source('system_set_default_permissions.py')
)
set_default_permissions.names.add(models.VerbName.objects.create(
    verb = set_default_permissions,
    name = 'set_default_permissions'
))
system.verbs.add(set_default_permissions)
set_default_permissions(set_default_permissions)
set_default_permissions(system)

# Create the first real user
wizard = create_object(name="Wizard", unique_name=True)
wizard.owner = wizard
wizard.save()
# Wizard owns the system...
system.owner = wizard
system.save()
# ...and the default permissions verb
set_default_permissions.owner = wizard
set_default_permissions.save()

with code.context(wizard, log.info):
    bag = create_object('bag of holding', location=wizard)
    hammer = create_object('wizard hammer', location=bag)
    book = create_object('class book', location=bag)
    players = create_object('player class', location=book)
    players.add_verb("look", "inspect", filename="players_look.py", repo=repo, ability=True, method=True)
    guests = create_object('guest class', location=book)
    guests.add_ancestors(players)
    authors = create_object('author class', location=book)
    authors.add_ancestors(players)
    programmers = create_object('programmer class', location=book)
    programmers.add_ancestors(authors)
    wizards = create_object('wizard class', location=book)
    wizards.add_ancestors(programmers)

    wizard.add_ancestors(wizards)

    rooms = create_object('room class', location=book)
    rooms.set_property("description", "There's not much to see here.", inherited=True)

    lab = create_object('The Laboratory')
    lab.add_ancestors(rooms)
    lab.set_property("description", """A cavernous laboratory filled with gadgetry of every kind,
    this seems like a dumping ground for every piece of dusty forgotten
    equipment a mad scientist might require.""")

    wizard.location = lab
    wizard.save()
