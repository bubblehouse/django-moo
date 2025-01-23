from moo.core import api

obj = args[0]  # pylint: disable=undefined-variable
obj.allow("wizards", "anything")
obj.allow("owners", "anything")
obj.allow("everyone", "read")

if obj.kind == "verb":
    obj.allow("everyone", "execute")
else:
    obj.allow("everyone", "read")
