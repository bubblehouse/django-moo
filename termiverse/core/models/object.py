from django.db import models

from .acl import AccessibleMixin

class Object(models.Model):
    name = models.CharField(max_length=255)
    unique_name = models.BooleanField(default=False)
    owner = models.ForeignKey('self', related_name='+', blank=True, null=True, on_delete=models.SET_NULL,)
    location = models.ForeignKey('self', related_name='contents', blank=True, null=True, on_delete=models.SET_NULL)
    parents = models.ManyToManyField('self', related_name='children', blank=True, symmetrical=False, through='Relationship')
    observers = models.ManyToManyField('self', related_name='observations', blank=True, symmetrical=False, through='Observation')

    def __str__(self):
        return "#%s (%s)" % (self.id, self.name)

class AccessibleObject(Object, AccessibleMixin):
    class Meta:
        proxy = True

    def owns(self, subject):
        pass

    def is_allowed(self, permission, subject, fatal=False):
        pass

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
