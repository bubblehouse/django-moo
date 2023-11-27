from django.db import models

class Property(models.Model):
    class Meta:
        verbose_name_plural = 'properties'

    name = models.CharField(max_length=255)
    value = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=255, choices=[(x,x) for x in ('string', 'python', 'dynamic')])
    owner = models.ForeignKey("Object", related_name='+', null=True, on_delete=models.SET_NULL)
    origin = models.ForeignKey("Object", related_name='properties', on_delete=models.CASCADE)

    def __str__(self):
        return '%s {#%s on %s}' % (self.name, self.id, self.origin)
