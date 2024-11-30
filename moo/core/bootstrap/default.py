import logging
import warnings

from django.conf import settings

from moo.core import models, bootstrap, code
from moo.core import create

log = logging.getLogger(__name__)

for name in settings.DEFAULT_PERMISSIONS:
    p = models.Permission.objects.create(name=name)

repo = models.Repository.objects.get(slug='default')
with warnings.catch_warnings():
    warnings.simplefilter('ignore', category=RuntimeWarning)
    system = create(name="System Object", unique_name=True)
    set_default_permissions = models.Verb.objects.create(
        method = True,
        origin = system,
        repo = repo,
        code = bootstrap.get_source('_system_set_default_permissions.py', dataset='default')
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

wizard.save()
# Wizard owns the system...
system.owner = wizard
system.save()
# ...and the default permissions verb
set_default_permissions.owner = wizard
set_default_permissions.save()

with code.context(wizard, log.info):
    bag = create('bag of holding', parents=[containers], location=wizard)
    hammer = create('wizard hammer', location=bag)
    book = create('class book', parents=[containers], location=bag)
    players = create('player class', location=book)

    guests = create('guest class', parents=[players], location=book)
    authors = create('author class', parents=[players], location=book)
    programmers = create('programmer class', parents=[authors], location=book)
    wizards = create('wizard class', parents=[programmers], location=book)

    wizard.parents.add(wizards)

    rooms = create('room class', parents=[containers], location=book)
    rooms.set_property("description", "There's not much to see here.", inherited=True)

    lab = create('The Laboratory', parents=[rooms])
    lab.set_property("description", """A cavernous laboratory filled with gadgetry of every kind,
    this seems like a dumping ground for every piece of dusty forgotten
    equipment a mad scientist might require.""")

    wizard.location = lab
    wizard.save()

    bootstrap.load_verbs(repo)
