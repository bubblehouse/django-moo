from moo.core import api

# pylint: disable=undefined-variable

obj = args[0]

obj.allow("wizards", "anything")
obj.allow("owners", "anything")
obj.allow("everyone", "read")

if obj.kind == "verb":
    obj.allow("everyone", "execute")
else:
    obj.allow("everyone", "read")
