#!moo verb test-async-verbs --on "player class" --dspec any

from moo.core import api, invoke

counter = 1
if args and len(args):  # pylint: disable=undefined-variable  # type: ignore
    counter = args[1] + 1  # pylint: disable=undefined-variable  # type: ignore

print(counter)

if counter < 10:
    verb = api.caller.get_verb("test-async-verbs")
    invoke(counter, verb=verb)
