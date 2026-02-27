#!moo verb set add --on $gender_utils

# pylint: disable=return-outside-function,undefined-variable

"""
This verb is used to set the pronoun properties of object, according to the `gender` specified. `gender` is a string:
one of the strings in the property list `$gender_utils.genders`, the list of recognized genders.

The verb checks `gender` against the gender list, and sets the pronouns on object with strings taken from property
lists stored on `$gender_utils`. If the gender change is successful, the (full) name of the gender (e.g., `female')
is returned. `None` is returned if `gender` does not match any recognized gender. Any other error encountered is
likewise rasied and the object's pronoun properties are left unaltered.
"""

obj = args[0]
gender = args[1]

try:
    index = _.gender_utils.genders.index(gender)
except:  # pylint: disable=bare-except
    return None
obj.set_property("gender", gender, inherit_owner=True)

for pronoun in _.gender_utils.pronouns:
    try:
        value = _.gender_utils.get_property(pronoun)[index]
        obj.set_property(pronoun, value, inherit_owner=True)
    except:  # pylint: disable=bare-except
        return None

return gender
