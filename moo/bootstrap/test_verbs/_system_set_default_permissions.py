# pylint: disable=undefined-variable

from moo.core import context, set_task_perms

obj = args[0]
with set_task_perms(context.player):
    obj.allow("wizards", "anything")
    obj.allow("owners", "anything")

    if obj.kind == "verb":
        obj.allow("everyone", "execute")
    elif obj.kind == "property":
        obj.allow("everyone", "read")
    elif obj.kind == "object":
        obj.allow("everyone", "read")
