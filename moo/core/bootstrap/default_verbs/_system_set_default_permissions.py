# pylint: disable=undefined-variable

obj = args[0]

obj.allow("wizards", "anything")
obj.allow("owners", "anything")
obj.allow("everyone", "read")

if obj.kind == "verb":
    obj.allow("everyone", "execute")
elif obj.kind == "object":
    obj.allow("everyone", "read")
