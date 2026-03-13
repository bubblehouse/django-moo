#!moo verb @reload reload --on $programmer --dspec any --ispec on:any

# pylint: disable=return-outside-function,undefined-variable

"""
Reload the source code for a filesystem-resident verb.
"""

from moo.core import context, VerbDoesNotExist

verb_name = context.parser.get_dobj_str() if context.parser else args[0]
target = context.parser.get_pobj("on", lookup=True) if context.parser else args[1]

try:
    verb = target.get_verb(verb_name)
except VerbDoesNotExist:
    return "That verb doesn't exist on %i(on)"
verb.reload()
