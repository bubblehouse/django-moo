from termiverse.core import models, bootstrap

from django.conf import settings

for name in settings.DEFAULT_PERMISSIONS:
    p = models.Permission.objects.create(name=name)

system = models.Object.objects.create(name="System Object", unique_name=True)

# Configure `set_default_permissions` the long way
set_default_permissions = models.Verb.objects.create(
    method = True,
    origin = system,
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
wizard = models.Object.objects.create(name="Wizard", unique_name=True)
wizard.owner = wizard
wizard.save()

# Wizard owns the system...
system.owner = wizard
system.save()

# ...and the default permissions verb
set_default_permissions.owner = wizard
set_default_permissions.save()
