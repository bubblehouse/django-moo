obj = args[0]  # pylint: disable=undefined-variable
obj.allow("wizards", "anything")
obj.allow("owners", "anything")

if obj.kind == "verb":
    obj.allow("everyone", "execute")
else:
    obj.allow("everyone", "read")
