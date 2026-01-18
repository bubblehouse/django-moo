#!moo verb test-nested-verbs-method --on "player class" --dspec this

from moo.core import api

counter = 1
if len(args):  # pylint: disable=undefined-variable
    counter = args[1] + 1  # pylint: disable=undefined-variable

print(counter)

if counter < 10:
    api.caller.invoke_verb("test-nested-verbs-method", counter)
