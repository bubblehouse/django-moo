#!moo verb test-nested-verbs test_nested_verbs --on "player class" --dspec none

# pylint: disable=return-outside-function,undefined-variable

from moo.core import context

print(1)
context.caller.invoke_verb("test-nested-verbs-method", 1)
