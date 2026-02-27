#!moo verb @gender --on $player --dspec either

# pylint: disable=return-outside-function,undefined-variable

"""
This verb is used to set the gender of a player object. Without any arguments, it prints the player's gender, currently
set pronouns and the available genders stored on `$gender_utils.genders`.

If a gender is given as the argument, gender, then the `$gender_utils.set` verb is called to actually change the
player's gender pronouns. If this verb does not return an error, then the gender of the player is set to the full
gender name which is returned. `$gender_utils:set` takes care of setting the correct pronouns.

If an error is returned when trying to set the player's gender, this could indicate that permission to change the
pronouns was denied, or some other problem existed. If a value of `None` is returned by `$gender_utils.set` then the
gender of the player is set, but the pronouns are left unchanged.

The gender of a player is used in the `$string_utils.pronoun_sub` verb to insert the appropriate pronouns in places
where `%' substitutions have been used. When the gender of a player is changed, it results in a set of 10 properties
being assigned on the player, one for every type of possible pronoun substitution. A further property, containing the
gender of the player, is also set, for example, to either "male", "female", or "neuter", depending on the argument
given to the `@gender` command.
"""

from moo.core import context

player = context.player
if context.parser.has_dobj_str():
    gender = context.parser.get_dobj_str()
    result = _.gender_utils.set(player, gender)
    if result is None:
        print(f"Error: Gender set to {gender}, but some pronouns are unchanged.")
    else:
        print(f"Gender set to {result}, and pronouns updated.")
else:
    print(f"Current gender: {player.gender}")
    print("Current pronouns:")
    print("  Subjective: " + player.ps + ", capitalized: " + player.psc)
    print("  Objective: " + player.po + ", capitalized: " + player.poc)
    print("  Possessive Adjective: " + player.pp + ", capitalized: " + player.ppc)
    print("  Reflexive: " + player.pr + ", capitalized: " + player.prc)
    print("  Quasi: " + player.pq + ", capitalized: " + player.pqc)
