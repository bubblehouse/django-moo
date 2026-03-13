#!moo verb explain --on $room

# pylint: disable=return-outside-function,undefined-variable

"""
Provide helpful information to the player should s/he fail to enter a command correctly. It is
called by the `huh2`` verb as a last resort to process the player command. The verb follows the parser``s search path
for verbs looking for a match with `verb`. If one is found, this means that the parser rejected the match because
the arguments did not match.

Having established this, `explain` compares the user input to the verb argument definition, and prints some
explanatory text to try and help the player enter a correct command. This verb usually catches mistakes such as
entering the wrong preposition, or forgetting to use an indirect object. It is provided as part of the $room class to
allow other room subclasses to provide more specific help for certain verbs defined in their rooms, if the user should
make an error trying to use one of them.
"""

from moo.core import context, VerbDoesNotExist

verb_name = args[0]
parser = context.parser

# Walk the same search order as Parser.get_verb(), without dspec/ispec filtering.
# We're looking for a verb matched by name but rejected due to argument mismatch.
search_order = parser.get_search_order()

found_verb = None
for obj in search_order:
    try:
        found_verb = obj.get_verb(verb_name, recurse=True)
    except VerbDoesNotExist:
        continue

if not found_verb:
    return

dspec = found_verb.direct_object
dobj_given = parser.has_dobj_str()

if dspec == "none" and dobj_given:
    print(f'The verb "{verb_name}" doesn\'t take a direct object.')
    return True
elif dspec in ("any", "this") and not dobj_given:
    print(f'The verb "{verb_name}" requires a direct object.')
    return True
