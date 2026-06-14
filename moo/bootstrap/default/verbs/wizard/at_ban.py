#!moo verb @ban ban_account --on $wizard --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
Staff command: ban an account (the scarring "toad").  Blocks the account and
blacklists its durable identity so the same human cannot simply re-register.
Keys to the account, not the avatar, and cannot target staff.
"""

from moo.sdk import context, account_for, ban

if not context.parser.has_dobj_str():
    print("Usage: @ban <player>")
    return

target = context.parser.get_dobj(lookup=True)
account = account_for(target)
if account is None:
    print(f"{target.name} has no account to ban.")
    return

try:
    ban(account)
except Exception as err:  # pylint: disable=broad-exception-caught
    print(str(err))
    return

print(f"Banned {target.name}.")
