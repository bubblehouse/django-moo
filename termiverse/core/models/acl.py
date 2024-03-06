import logging

from django.db import models

from .. import code

log = logging.getLogger(__name__)

class AccessibleMixin(object):
    """
    The base class for all Objects, Verbs, and Properties.
    """
    def check_permission(self, permission, subject):
        """
        Check if the current caller has permission for something.
        """
        caller = code.get_caller()
        if not caller:
            return
        if permission == 'grant' and caller.owns(subject):
            return
        caller.is_allowed(permission, subject, fatal=True)

    def allow(self, accessor, permission):
        """
        Allow a certain object or group to do something on this object.

        [ACL] allowed to grant on this (or owner of this)
        """
        self.check_permission('grant', self)
        Access.objects.create(
            object = self if self.kind == 'object' else None,
            verb = self if self.kind == 'verb' else None,
            property = self if self.kind == 'property' else None,
            rule = 'allow',
            permission = Permission.objects.get(name=permission),
            type = 'group' if isinstance(accessor, str) else 'accessor',
            accessor = None if isinstance(accessor, str) else accessor,
            group = accessor if isinstance(accessor, str) else None,
        )

    def deny(self, accessor, permission):
        """
        Deny a certain object or group from doing something on this object.

        [ACL] allowed to grant on this (or owner of this)
        """
        self.check_permission('grant', self)
        Access.objects.create(
            object = self if self.kind == 'object' else None,
            verb = self if self.kind == 'verb' else None,
            property = self if self.kind == 'property' else None,
            rule = 'deny',
            permission = Permission.objects.get(name=permission),
            type = 'group' if isinstance(accessor, str) else 'accessor',
            accessor = None if isinstance(accessor, str) else accessor,
            group = accessor if isinstance(accessor, str) else None,
        )

class Permission(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class Access(models.Model):
    class Meta:
        verbose_name_plural = 'access controls'
        unique_together = ('object', 'verb', 'property', 'rule', 'permission', 'type', 'accessor', 'group', 'weight')

    object = models.ForeignKey("Object", related_name='acl', null=True, on_delete=models.CASCADE)
    verb = models.ForeignKey("Verb", related_name='acl', null=True, on_delete=models.CASCADE)
    property = models.ForeignKey("Property", related_name='acl', null=True, on_delete=models.CASCADE)
    rule = models.CharField(max_length=5, choices=[(x,x) for x in ('allow', 'deny')])
    permission = models.ForeignKey(Permission, related_name='usage', on_delete=models.CASCADE)
    type = models.CharField(max_length=8, choices=[(x,x) for x in ('accessor', 'group')])
    accessor = models.ForeignKey("Object", related_name='rights', null=True, on_delete=models.CASCADE)
    group = models.CharField(max_length=8, null=True, choices=[(x,x) for x in ('everyone', 'owners', 'wizards')])
    weight = models.IntegerField(default=0)

    def actor(self):
        return self.accessor if self.type == 'accessor' else self.group

    def entity(self):
        if self.object:
            return 'self'
        elif self.verb:
            return ''.join([
                ['', '@'][self.verb.ability],
                self.verb.names.all()[:1][0].name,
                ['', '()'][self.verb.method],
            ])
        else:
            return self.property.name

    def origin(self):
        if self.object:
            return self.object
        elif self.verb:
            return self.verb.origin
        else:
            return self.property.origin

    def __str__(self):
        try:
            return '%(rule)s %(actor)s %(permission)s on %(entity)s (%(weight)s)' % dict(
                rule        = self.rule,
                actor        = self.actor(),
                permission    = self.permission.name,
                entity        = self.entity(),
                weight        = self.weight,
            )
        except Exception as e:
            import traceback
            traceback.print_exc();
            return str(e)
