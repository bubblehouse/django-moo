#!moo verb @reload reload --on $programmer --dspec any --ispec on:any

# pylint: disable=return-outside-function,undefined-variable

"""
This verb is used to reload the source code for a filesystem-resident verb.
"""

from moo.core import context

verb_name = context.parser.get_dobj_str() if context.parser else args[0]
target = context.parser.get_pobj("on") if context.parser else args[1]

if not target.has_verb(verb_name):
    return "That verb doesn't exist on %i(on)"
verb = target.get_verb(verb_name)
verb.reload()
