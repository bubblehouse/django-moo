#!moo verb look_self --on $player

# pylint: disable=return-outside-function,undefined-variable

"""
This verb overrides the `$root_class` definition to provide an indication to other players of whether this player is
currently active or not. It uses `passthrough()` to allow the parent class to print a description, and then looks at
the `connected_players()` list to determine if this player is currently connected. If not, then the text

    He is sleeping

is printed. If the player is connected, and has been idle for less than 60 seconds, then the string

    He is awake and looks alert

is printed. If the player is connected, but has been inactive for more than 60 seconds, the string

    He is awake, but has been staring off into space for X

is printed, where X is an indication of the time the player has been inactive. The gender pronoun inserted is taken
from the pronoun list for the player. This means it can vary with the gender of the player object.

If the player is carrying any objects, a simple list of these is printed.
"""

passthrough()
print(_.sprintf("%S is sleeping."))

# # TODO: implement this
# if this not in connected_players():
#     print("He is sleeping.")
# elif this.idle_time() < 60:
#     print("He is awake and looks alert.")
# else:
#     print(f"He is awake, but has been staring off into space for {this.idle_time()} seconds.")
