from .models import verb, object, property, auth, task
from django.contrib import admin

class VerbInline(admin.TabularInline):
    model = verb.Verb
    fk_name = 'origin'
    extra = 1
    exclude = ('code',)
    readonly_fields = ('filename', 'ability', 'method', 'owner')

class PropertyInline(admin.TabularInline):
    model = property.Property
    fk_name = 'origin'
    extra = 1
    readonly_fields = ('name', 'value', 'owner')

class ObjectAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'unique_name', 'owner', 'location')
    inlines = [
        VerbInline,
        PropertyInline,
    ]
admin.site.register(object.Object, ObjectAdmin)

admin.site.register(verb.Verb)
admin.site.register(property.Property)
admin.site.register(auth.Permission)

class AccessAdmin(admin.ModelAdmin):
    list_display = ('rule', 'actor', 'action', 'entity', 'origin')

    def actor(self, obj):
        return obj.actor()

    def entity(self, obj):
        return obj.entity()

    def origin(self, obj):
        return obj.origin()

    def action(self, obj):
        return obj.permission.name
admin.site.register(auth.Access, AccessAdmin)

admin.site.register(auth.Player)
admin.site.register(task.Task)
