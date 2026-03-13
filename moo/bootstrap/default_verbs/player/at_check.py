#!moo verb @check --on $player --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
This is a player command used to check the origin of the last few messages received by the player. The `args` list can
contain the number of lines to print as the first element, followed by a list of player names. Each player name in the
list is a person to be trusted, unless the name is prefixed by an exclamation point, ``!``, in which case the person is
not to be trusted.

The verb starts by building up a list of trusted and mistrusted individuals based on the names given on the command
line. Then it runs through last `n`` messages in the player``s `responsible` property list, checking the origin of the
messages using the `this.whodunnit` verb with the `trust` and `mistrust` lists.

Any dubious messages found are printed, along with details of who sent them.
"""

from moo.core import context, lookup

player = context.player
args = context.parser.words[1:] if context.parser else args
trust = []
mistrust = []
linecount = int(args.pop(0))
for name in args:
    if name.startswith('!'):
        mistrust.append(lookup(name[1:]))
    else:
        trust.append(lookup(name))

for frame in player.responsible[-linecount:]:
    callers, saved_args = frame
    non_wizard = player.whodunnit(callers, trust, mistrust)
    if non_wizard:
        print(f"{non_wizard['caller']} sent message '{saved_args[0]}' using verb '{non_wizard['verb_name']}' in {non_wizard['this']}")
