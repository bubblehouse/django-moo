#!moo verb test-nested-verbs --on "player class" --ability

from moo.core import api

print(1)
api.caller.invoke_verb("test-nested-verbs-method", 1)
