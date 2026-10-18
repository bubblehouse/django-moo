#!moo verb @whereis whereis --on $player --dspec either

# pylint: disable=return-outside-function,undefined-variable

"""
Locate players in the virtual world. Any player may locate any other player.

With no argument, the verb lists where every connected player is. With an
argument, it looks up each name and reports the string returned by each match's
``whereis_location_msg`` verb, then names any that did not match. Called as a
method, each argument is a name to look up.
"""

from moo.sdk import context, lookup, account_for, connected_players, NoSuchObjectError

if args:
    targets = list(args)
elif context.parser is not None and context.parser.has_dobj_str():
    targets = [context.parser.get_dobj_str()]
else:
    targets = None

matched = []
unmatched = []
if targets is None:
    matched = list(connected_players())
    if not matched:
        print("No players are currently connected.")
        return
else:
    for target in targets:
        try:
            matched.append(lookup(target))
        except NoSuchObjectError:
            unmatched.append(target)

if matched:
    print("Found the following players:")
for player in matched:
    line = player.whereis_location_msg()
    # Staff see the account behind a name, which may be a persona.
    account = account_for(player) if context.player.is_wizard() else None
    if account is not None:
        line += f" (acct {account.pk})"
    print(line)
for name in unmatched:
    print(f"There is no player named {name!r}.")
