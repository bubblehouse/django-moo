#!moo verb test-nested-verbs --on "player class" --ability --method

from moo.core import api

counter = 1
if args and len(args):  # pylint: disable=undefined-variable
    counter = args[0] + 1  # pylint: disable=undefined-variable

print(counter)

if counter < 10:
    api.caller.invoke_verb('test-nested-verbs', counter)
