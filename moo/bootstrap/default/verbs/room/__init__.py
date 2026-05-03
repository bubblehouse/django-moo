"""
The Room Class is the basic class from which all the rooms in the virtual world are descended. It is one of the very
basic classes essential to constructing a virtual world; an exit is the other essential class.

A room can be thought of as a container for players and objects. It can have a number of exits that connect it to other
rooms. These exits are directed; they lead from one room to another room. For a two way passage to exist, two exits are
needed, going in opposite directions.

The room class defines a lot of verbs, which are used to provide an interface to the properties of the room.

One special point is worth noting about rooms and exits. An exit can have an arbitrary name - indeed, this is the usual
case. In order for the room to recognise the exit name, and match it up with an exit that exists in the room, some form
of catchall mechanism is used. If a player types a sentence that the parser cannot match with anything, it executes a
verb called `huh` in the current room, if one exists.

When this happens, the `huh`` verb is free to take the player``s sentence, search for a valid exit, and act accordingly.
This mechanism provides a very flexible arrangement for dealing with exits, and also allows a degree of player help to
be added. If a close match to a command is found, the `huh` verb could detect this and provide a useful response that
would help the player construct the correct sentence.
"""
