#!moo verb @sw*eep --on $player

# pylint: disable=return-outside-function,undefined-variable,no-name-in-module

"""
This is a player command used to list the objects that are capable of receiving any messages sent out from the player
in the current room. It gathers a list of the objects in the current room, from the `contents`` property of the player``s
location. If any element in the list is a connected player, the message

    blip (#42) is listening.

is printed, for example.

If an element has a `sweep_msg`` verb defined, the returned string from this verb is printed, prepended by the object``s
name.

If an element has a `tell` verb defined, and the owner is not the invoking player or a wizard, then this object is a
potential snooper, and is reported by a phrase such as:

    The Fruitbat (#999) has been taught to listen by blip (#42).

The verbs ``announce``, ``announce_all``, ``announce_all_but``, ``say``, ``emote``, ``huh``, ``huh2`` and ``whisper`` are checked to
see if the current room has a definition not owned by the invoking player or a wizard. If any of these are found, a
message such as:

    The Venue Hallway (#1234) may have been bugged by blip.

if the player's location was The Venue Hallway.

If no potential bugs are found, the the message ``Communications are secure.`` is printed, and the player can breathe
easily (ish).
"""
from moo.sdk import context, NoSuchVerbError

buggable_verbs = ["announce", "announce_all", "announce_all_but", "say", "emote", "huh", "huh2", "whisper"]

player = context.player
room = player.location
secure = True
for obj in room.contents.all():
    if obj.is_player():
        print(f"{obj} is listening.")
    try:
        print(f"{obj} {obj.invoke_verb('sweep_msg')}")
    except NoSuchVerbError:
        pass
    try:
        tell = obj.get_verb("tell")
        if tell.owner != player and not tell.owner.is_wizard():
            secure = False
            print(f"{obj} has been taught to listen by {tell.owner}.")
    except NoSuchVerbError:
        pass
already_printed = {}
for verb in buggable_verbs:
    try:
        v = room.get_verb(verb)
        if v.owner != player and not v.owner.is_wizard():
            msg = f"{room} may have been bugged by {v.owner}."
            if msg not in already_printed:
                already_printed[msg] = True
                secure = False
                print(msg)
    except NoSuchVerbError:
        pass
if secure:
    print("Communications are secure.")
