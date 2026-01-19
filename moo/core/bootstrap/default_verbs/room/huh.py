#!moo verb huh --on $room

"""
This verb is a stub used to call the huh2 verb. It is called by the LambdaMOO server when it can't match a sentence
given to it by a player. The server calls `huh` with verb equal to the actual verb in the erroneous command line.
This means it is not possible to use passthrough() if you override `huh` in a room; it would pass control up to a verb on
the parent named verb, i.e., whatever the verb was on the command line. This, by definition, doesn't exist. To get
around this, and allow you to use passthrough() to get the default `huh` behaviour, `huh` calls `huh2`. You should override
`huh2` if you wish to be able to use passthrough() to get the default `huh` behaviour.
"""

return this.huh2(args[0])
