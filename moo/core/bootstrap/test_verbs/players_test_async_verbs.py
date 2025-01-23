#!moo verb test-async-verbs --on "player class" --ability --method

from moo.core import api, invoke

counter = 1
if args and len(args):  # pylint: disable=undefined-variable
    counter = args[0] + 1  # pylint: disable=undefined-variable

print(counter)

if counter < 10:
    verb = api.caller.get_verb("test-async-verbs")
    invoke(counter, verb=verb)
