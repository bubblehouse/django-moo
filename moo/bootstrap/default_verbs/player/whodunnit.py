#!moo verb whodunnit --on $player

# pylint: disable=return-outside-function,undefined-variable

"""
This verb runs through the list of callers until it finds an object reference that is not a wizard, is not in the list
`trust`, or is in the list `mistrust`. The verb is used by `$player:tell` to locate the originator of a message. It
returns dictionary of several elements, in a similar format as that saved in `context.caller_stack`:

    dict(
        caller           # Player with whose permissions the verb is running
        this             # Object where the verb was located
        verb_name        # Name used to invoke the chosen verb
    )
"""

callers = args[0]
trust = args[1]
mistrust = args[2]

for frame in callers:
    caller = frame["caller"]
    if caller.is_wizard():
        continue
    if caller in trust:
        continue
    if caller in mistrust:
        return dict(
            this = frame["this"],
            verb_name = frame["verb_name"],
            caller = caller,
        )
return None
