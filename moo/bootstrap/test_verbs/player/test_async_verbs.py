#!moo verb test-async-verbs --on "player class" --dspec any

# pylint: disable=return-outside-function,undefined-variable

from moo.core import context, invoke

counter = 1
if args and len(args):  # pylint: disable=undefined-variable  # type: ignore
    counter = args[0] + 1  # pylint: disable=undefined-variable  # type: ignore

print(counter)

if counter < 10:
    verb = context.caller.get_verb("test-async-verbs")
    invoke(counter, verb=verb)
