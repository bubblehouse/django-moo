#!moo verb test-nested-verbs-method --on "player class" --dspec this

# pylint: disable=return-outside-function,undefined-variable

from moo.core import context

counter = 1
if len(args):  # pylint: disable=undefined-variable
    counter = args[0] + 1  # pylint: disable=undefined-variable

print(counter)

if counter < 10:
    context.caller.invoke_verb("test-nested-verbs-method", counter)
