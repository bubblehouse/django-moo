#!moo verb @ban ban_account @unban unban_account --on $wizard --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
Staff command: ban an account (the scarring "toad").  Blocks the account and
blacklists its durable identity so the same human cannot simply re-register.
Keys to the account, not the avatar, and cannot target staff. ``@unban
<player>`` lifts the ban and drops the identity from this Site's blacklist.
Add ``because <reason>`` to either to record why in the audit log.
"""

from moo.sdk import context, account_for, ban, unban

# This verb runs as its Wizard owner, so it checks the player who typed it.
if not context.player.is_wizard():
    print("Permission denied.")
    return

lifting = "unban" in verb_name
if not context.parser.has_dobj_str():
    print("Usage: @unban <player> [because <reason>]" if lifting else "Usage: @ban <player> [because <reason>]")
    return

parsed = _.wizard.sanction_args()
target, reason = parsed[0], parsed[2]
if target is None:
    return
account = account_for(target)
if account is None:
    print(f"{target.name} has no account to {'unban' if lifting else 'ban'}.")
    return

try:
    if lifting:
        unban(account, reason=reason)
    else:
        ban(account, reason=reason)
except Exception as err:  # pylint: disable=broad-exception-caught
    print(str(err))
    return

print(f"Unbanned {target.name}." if lifting else f"Banned {target.name}.")
