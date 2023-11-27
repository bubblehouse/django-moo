from django.db import models

class Permission(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class Access(models.Model):
    class Meta:
        verbose_name_plural = 'access controls'

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

class Player(models.Model):
    avatar = models.ForeignKey("Object", null=True, on_delete=models.SET_NULL)
    session_id = models.CharField(max_length=255, null=True, blank=True)
    wizard = models.BooleanField(default=False)
    enabled = models.BooleanField(default=True)
    crypt = models.CharField(max_length=255, null=True, blank=True)
    last_login = models.DateTimeField(null=True)
    last_logout = models.DateTimeField(null=True)

    def __str__(self):
        return self.email

    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_staff(self):
        return self.wizard

    @property
    def is_superuser(self):
        return self.wizard

    def has_module_perms(self, app):
        return True

    def has_perm(self, perm):
        return True

    @property
    def email(self):
        return self.avatar.name + '@antioch.net'
