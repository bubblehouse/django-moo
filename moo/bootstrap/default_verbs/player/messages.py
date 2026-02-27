#!moo verb page_absent_msg page_origin_msg page_echo_msg whereis_location_msg who_location_msg --on $player

# pylint: disable=undefined-variable,return-outside-function

"""
These verbs return a pronoun substituted version of the corresponding properties stored on the player object.
They are used by the `page` verb, and the `whereis` and `who` commands.
"""

if verb_name == "page_absent_msg":
    return _sprintf(this.page_absent_msg)
elif verb_name == "page_origin_msg":
    return _sprintf(this.page_origin_msg)
elif verb_name == "page_echo_msg":
    return _sprintf(this.page_echo_msg)
elif verb_name == "whereis_location_msg":
    return _sprintf(this.whereis_location_msg)
elif verb_name == "who_location_msg":
    return _sprintf(this.who_location_msg)
else:
    raise ValueError(f"Unknown verb name: {verb_name}")
