#!moo verb @gripe --on $player --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
A gripe is a player complaint or observation that is sent, using MOO mail, to all the administrators in the game. It is
intended to provide a way to report problems with the MOO in a high-priority way that will attract the attention of the
people who can do something about it. A good example of the use of a gripe is to complain about a bug in one of the
core classes, or maybe even a request for something to be added.

The implementation of the gripe concept involves a property on the System Object called `$gripe_recipients`. This is a
list of all the players who will be mailed the `@gripe` message. When a player types in `@gripe` they are taken to the
mail room to enter their message. Any text entered on the line with the `@gripe` command is taken to be the subject of
the gripe message. When the message is finished and sent, it is received by all the people on the `$gripe_recipients`
list.
"""

print("@gripe is not yet implemented.")
