#!moo verb exam*ine --on "Root Class" --dspec any

"""
This prints out some useful information about the object to the player. It is provided as a player command, to allow
every player to determine basic information about any other objects they come across. For example:

>exam #0
The System Object (#0) is owned by Wizard (#2).
Aliases:  The, Known, and Universe
(No description set.)

The idea is to allow every player to discover the owner, full name, description and aliases of any object.

If you control the object, the lock for the object is shown. If the object has other objects inside it, then the
contents list is printed out, too. If the object has verbs defined on it, then these verbs are listed, provided
they are readable.
"""

from moo.core import api
obj = api.parser.get_dobj()

print(f"{obj.name} (#{obj.id} ) is owned by {obj.owner.name} (#{obj.owner.id}).")
if obj.aliases:
    print("Aliases: ", end="")
    print(", ".join(obj.aliases.values("alias")))
print(obj.description())
# TODO: display lock info if the player controls the object
# TODO: display contents if there are any
# TODO: display verbs if there are any and they are readable
