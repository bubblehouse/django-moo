#!moo verb exam*ine --on $root_class --dspec any

# pylint: disable=return-outside-function,undefined-variable

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

from moo.core import context
obj = context.parser.get_dobj()

print(f"{obj.name} (#{obj.id} ) is owned by {obj.owner.name} (#{obj.owner.id}).")
if obj.parents.exists():
    print("Parents:")
    for parent in obj.parents.all():
        print(f"  {parent.name} (#{parent.id})")
if obj.aliases.exists():
    print("Aliases: ")
    print(", ".join(obj.aliases.values("alias")))
print(obj.description())

# display lock info if the player controls the object
if context.player.owns(obj):
    print("Key: ")
    if obj.key:
        print(obj.key)
    else:
        print("(no key)")

# display contents if there are any
if obj.contents.exists():
    print("Contents:")
    for item in obj.contents.all():
        print(f"  {item.name} (#{item.id})")

# display verbs if there are any and they are readable
if obj.verbs.exists():
    print("Verbs:")
    for verb in obj.verbs.all():
        if context.player.is_allowed('read', verb):
            print(f"  {verb.name()}")
        else:
            print(f"  {verb.name()} (unreadable)")
