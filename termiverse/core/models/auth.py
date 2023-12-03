from django.db import models

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
