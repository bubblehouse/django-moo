#!moo verb test-nested-verbs --on "player class" --dspec none

# pylint: disable=return-outside-function,undefined-variable

from moo.core import api

print(1)
api.caller.invoke_verb("test-nested-verbs-method", 1)
