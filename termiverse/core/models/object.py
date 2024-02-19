import logging

from django.db import models
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from .. import bootstrap
from ..code import get_caller
from .acl import AccessibleMixin, Access
from .verb import AccessibleVerb, VerbName
from .property import AccessibleProperty

log = logging.getLogger(__name__)

def create_object(name, *a, **kw):
    kw['name'] = name
    if 'owner' not in kw:
        kw['owner'] =  get_caller()
    if 'location' not in kw and kw['owner']:
        kw['location'] = kw['owner'].location
    return AccessibleObject.objects.create(*a, **kw)

@receiver(m2m_changed)
def relationship_changed(sender, instance, action, model, signal, reverse, pk_set, using):
    if not(sender is Relationship and action == "post_add" and not reverse):
        return
    child = instance
    for pk in pk_set:
        parent = model.objects.get(pk=pk)
        for property in AccessibleProperty.objects.filter(origin=parent, inherited=True):
            AccessibleProperty.objects.update_or_create(
                name = property.name,
                origin = child,
                defaults = dict(
                    owner = child.owner,
                    inherited = property.inherited,
                ),
                create_defaults = dict(
                    owner = child.owner,
                    inherited = property.inherited,
                    value = property.value,
                    type = property.type,
                )
            )

class Object(models.Model):
    name = models.CharField(max_length=255)
    unique_name = models.BooleanField(default=False)
    owner = models.ForeignKey('self', related_name='+', blank=True, null=True, on_delete=models.SET_NULL,)
    location = models.ForeignKey('self', related_name='contents', blank=True, null=True, on_delete=models.SET_NULL)
    parents = models.ManyToManyField('self', related_name='children', blank=True, symmetrical=False, through='Relationship')

    def __str__(self):
        return "#%s (%s)" % (self.id, self.name)

    @property
    def kind(self):
        return 'object'

    def get_ancestors(self):
        """
        Get the ancestor tree for this object.
        """
        # TODO: One day when Django 5.0 works with `django-cte` this can be SQL.
        ancestors = []
        for parent in self.parents.all():
            ancestors.append(parent)
            ancestors.extend(parent.get_ancestors())
        return ancestors

    def get_descendents(self):
        """
        Get the descendent tree for this object.
        """
        # TODO: One day when Django 5.0 works with `django-cte` this can be SQL.
        descendents = []
        for child in self.children.all():
            descendents.append(child)
            descendents.extend(child.get_descendents())
        return descendents

    def add_verb(self, *names, code=None, owner=None, repo=None, filename=None, ability=False, method=False):
        owner = get_caller() or owner or self
        if filename:
            code = bootstrap.get_source(filename)
        verb = AccessibleVerb.objects.create(
            method = method,
            ability = ability,
            origin = self,
            owner = owner,
            repo = repo,
            filename = filename,
            code = code
        )
        for name in names:
            verb.names.add(VerbName.objects.create(
                verb=verb,
                name=name
            ))

    def invoke_verb(self, name, *args, **kwargs):
        qs = AccessibleVerb.objects.filter(origin=self, names__name=name)
        if not qs:
            for ancestor in self.get_ancestors():
                qs = AccessibleVerb.objects.filter(origin=ancestor, names__name=name)
                if qs:
                    break
        if qs:
            qs[0](*args, **kwargs)
        else:
            raise AccessibleVerb.DoesNotExist(f"No such verb `{name}`.")

    def set_property(self, name, value, inherited=False, owner=None):
        owner = get_caller() or owner or self
        AccessibleProperty.objects.update_or_create(
            name = name,
            origin = self,
            defaults = dict(
                value = value,
                owner = owner,
                type = "string",
                inherited = inherited,
            )
        )

    def get_property(self, name, recurse=True, original=False):
        qs = AccessibleProperty.objects.filter(origin=self, name=name)
        if not qs and recurse:
            for ancestor in self.get_ancestors():
                qs = AccessibleProperty.objects.filter(origin=ancestor, name=name)
                if qs:
                    break
        if qs:
            return qs[0] if original else qs[0].value
        else:
            raise AccessibleProperty.DoesNotExist(f"No such property `{name}`.")

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

    child = models.ForeignKey(Object, related_name='+', on_delete=models.CASCADE)
    parent = models.ForeignKey(Object, related_name='+', on_delete=models.CASCADE)
    weight = models.IntegerField(default=0)

class Alias(models.Model):
    class Meta:
        verbose_name_plural = 'aliases'

    object = models.ForeignKey(Object, related_name='aliases', on_delete=models.CASCADE)
    alias = models.CharField(max_length=255)
