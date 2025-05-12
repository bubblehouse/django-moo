# -*- coding: utf-8 -*-
"""
Django backend admin support.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User  # pylint: disable=imported-auth-user

from .forms import VerbAdminForm
from .models import acl, auth, object, property, task, verb  # pylint: disable=redefined-builtin


class VerbInline(admin.TabularInline):
    model = verb.Verb
    fk_name = "origin"
    extra = 1
    exclude = ("code",)
    readonly_fields = ("filename", "direct_object", "owner")


class PropertyInline(admin.TabularInline):
    model = property.Property
    fk_name = "origin"
    extra = 1
    readonly_fields = ("name", "value", "owner")


@admin.register(object.Object)
class ObjectAdmin(admin.ModelAdmin):
    list_display = ("__str__", "unique_name", "owner", "location")
    inlines = [
        VerbInline,
        PropertyInline,
    ]
    raw_id_fields = ("owner", "location")


@admin.register(verb.Verb)
class VerbAdmin(admin.ModelAdmin):
    form = VerbAdminForm
    raw_id_fields = ("owner", "origin")


@admin.register(verb.VerbName)
class VerbNameAdmin(admin.ModelAdmin):
    raw_id_fields = ("verb",)


@admin.register(verb.Preposition)
class PrepositionAdmin(admin.ModelAdmin):
    list_display = ("prepositions",)

    def prepositions(self, obj):
        return ", ".join([name.name for name in obj.names.all()])


@admin.register(property.Property)
class PropertyAdmin(admin.ModelAdmin):
    raw_id_fields = ("owner", "origin")


admin.register(acl.Permission)


@admin.register(acl.Access)
class AccessAdmin(admin.ModelAdmin):
    list_display = ("rule", "actor", "action", "entity", "origin")
    raw_id_fields = ("object", "verb", "property", "accessor")

    def actor(self, obj):
        return obj.actor()

    def entity(self, obj):
        return obj.entity()

    def origin(self, obj):
        return obj.origin()

    def action(self, obj):
        return obj.permission.name


class PlayerInline(admin.StackedInline):
    model = auth.Player
    can_delete = False


admin.site.unregister(User)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [PlayerInline]


admin.register(task.Task)
