obj = args[0]  # pylint: disable=undefined-variable
obj.allow("wizards", "anything")
obj.allow("owners", "anything")

if obj.kind == "verb":
    obj.allow("everyone", "execute")
elif obj.kind == "object":
    obj.allow("everyone", "read")
