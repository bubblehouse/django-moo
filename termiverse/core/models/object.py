from django.db import models

from .. import bootstrap
from .acl import AccessibleMixin, Access
from .verb import AccessibleVerb, VerbName
from .property import AccessibleProperty

class Object(models.Model):
    name = models.CharField(max_length=255)
    unique_name = models.BooleanField(default=False)
    owner = models.ForeignKey('self', related_name='+', blank=True, null=True, on_delete=models.SET_NULL,)
    location = models.ForeignKey('self', related_name='contents', blank=True, null=True, on_delete=models.SET_NULL)
    parents = models.ManyToManyField('self', related_name='children', blank=True, symmetrical=False, through='Relationship')
    observers = models.ManyToManyField('self', related_name='observations', blank=True, symmetrical=False, through='Observation')

    def __str__(self):
        return "#%s (%s)" % (self.id, self.name)

    @property
    def kind(self):
        return 'object'

    def add_verb(self, *names, code=None, filename=None, method=False):
        verb = AccessibleVerb.objects.create(
            method = method,
            origin = self,
            code = bootstrap.get_source(filename) if filename else code
        )
        for name in names:
            verb.names.add(VerbName.objects.create(
                verb=verb,
                name=name
            ))
        set_default_permissions = AccessibleVerb.objects.get(
            origin = Object.objects.get(pk=1),
            names__name = 'set_default_permissions'
        )
        set_default_permissions(verb)
        self.verbs.add(verb)

    def add_property(self, name, value):
        prop = AccessibleProperty.objects.create(
            name = name,
            value = value,
            origin = self,
            type = "python"
        )
        set_default_permissions = AccessibleVerb.objects.get(
            origin = Object.objects.get(pk=1),
            names__name = 'set_default_permissions'
        )
        set_default_permissions(prop)
        self.properties.add(prop)

class AccessibleObject(Object, AccessibleMixin):
    class Meta:
        proxy = True

    def owns(self, subject):
        return subject.owner == self

    def is_allowed(self, permission, subject, fatal=False):
        rules = Access.objects.filter(
            object = subject if subject.kind == 'object' else None,
            verb = subject if subject.kind == 'verb' else None,
            property = subject if subject.kind == 'property' else None,
            type = 'accessor',
            accessor = self,
            permission__in = (permission, "anything")
        )
        rules.union(Access.objects.filter(
            object = subject if subject.kind == 'object' else None,
            verb = subject if subject.kind == 'verb' else None,
            property = subject if subject.kind == 'property' else None,
            type = 'group',
            group = 'everyone',
            permission__in = (permission, "anything")
        ))
        if self.owns(subject):
            rules.union(Access.objects.filter(
                object = subject if subject.kind == 'object' else None,
                verb = subject if subject.kind == 'verb' else None,
                property = subject if subject.kind == 'property' else None,
                type = 'group',
                group = 'owners',
                permission__in = (permission, "anything")
            ))
        if self.is_wizard():
            rules.union(Access.objects.filter(
                object = subject if subject.kind == 'object' else None,
                verb = subject if subject.kind == 'verb' else None,
                property = subject if subject.kind == 'property' else None,
                type = 'group',
                group = 'wizards',
                permission__in = (permission, "anything")
            ))
        if rules:
            for rule in rules.order_by("rule", "type"):
                if fatal and rule.rule == 'deny':
                    raise PermissionError(f"{self} is explicitly denied {permission} on {subject}")
                else:
                    return False
            return True
        elif fatal:
            raise PermissionError(f"{self} is not allowed {permission} on {subject}")
        else:
            return False

class Relationship(models.Model):
    class Meta:
        unique_together = [['child', 'parent']]

    child = models.ForeignKey(Object, related_name='parent', on_delete=models.CASCADE)
    parent = models.ForeignKey(Object, related_name='child', on_delete=models.CASCADE)
    weight = models.IntegerField(default=0)

class Observation(models.Model):
    object = models.ForeignKey(Object, related_name='observer', on_delete=models.CASCADE)
    observer = models.ForeignKey(Object, related_name='object', on_delete=models.CASCADE)

class Alias(models.Model):
    class Meta:
        verbose_name_plural = 'aliases'

    object = models.ForeignKey(Object, related_name='aliases', on_delete=models.CASCADE)
    alias = models.CharField(max_length=255)
