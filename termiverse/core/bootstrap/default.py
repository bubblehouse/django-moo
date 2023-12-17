from termiverse.core import models, bootstrap, code

from django.conf import settings

create_object = models.Object.objects.create

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

bag = create_object(
    name = 'bag of holding',
    owner = wizard,
    location = wizard,
)

hammer = create_object(
    name = 'wizard hammer',
    owner = wizard,
    location = bag,
)

book = create_object(
    name = 'class book',
    owner = wizard,
    location = bag,
)

players = create_object(
    name = 'player class',
    owner = wizard,
    location = book,
)
with code.context(wizard):
    players.add_verb(["look", "inspect"], filename="players_look.py", ability=True)

guests = create_object(
    name = 'guest class',
    owner = wizard,
    location = book,
)
guests.parents.add(players)

authors = create_object(
    name = 'author class',
    owner = wizard,
    location = book,
)
authors.parents.add(players)

programmers = create_object(
    name = 'programmer class',
    owner = wizard,
    location = book,
)
programmers.parents.add(authors)

wizards = create_object(
    name = 'wizard class',
    owner = wizard,
    location = book,
)
wizards.parents.add(programmers)

wizard.parents.add(wizards)

rooms = create_object(
    name = 'room class',
    owner = wizard,
    location = book,
)

lab = create_object(
    name = 'The Laboratory',
    owner = wizard,
)
lab.parents.add(rooms)
with code.context(wizard):
    lab.add_property("description", """A cavernous laboratory filled with gadgetry of every kind,
    this seems like a dumping ground for every piece of dusty forgotten
    equipment a mad scientist might require.""")

wizard.location = lab
wizard.save()
