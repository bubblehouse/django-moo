from termiverse.core import models, bootstrap

from django.conf import settings

for name in settings.DEFAULT_PERMISSIONS:
    p = models.Permission.objects.create(name=name)

system = models.Object.objects.create(name="System Object")
verb = models.Verb.objects.create(
    method = True,
    origin = system,
    code = bootstrap.get_source('system_set_default_permissions.py')
)
name = models.VerbName.objects.create(verb=verb, name='set_default_permissions')
verb.names.add(name)
system.verbs.add(verb)

verb(verb)
verb(system)
