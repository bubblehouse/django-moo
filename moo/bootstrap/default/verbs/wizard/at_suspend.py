#!moo verb @suspend suspend_account --on $wizard --dspec any --ispec for:any

# pylint: disable=return-outside-function,undefined-variable

"""
Staff command: suspend an account, blocking its login for a period (the
reversible "newt").  ``@suspend <player>`` is open-ended; ``@suspend <player>
for <hours>`` sets a deadline after which login is allowed again. Add
``because <reason>`` to record why in the audit log. Keys to the account, not
the avatar, and cannot target staff.
"""

from moo.sdk import context, account_for, suspend

# This verb runs as its Wizard owner, so it checks the player who typed it.
if not context.player.is_wizard():
    print("Permission denied.")
    return

if not context.parser.has_dobj_str():
    print("Usage: @suspend <player> [for <hours>] [because <reason>]")
    return

target, raw, reason = _.wizard.sanction_args()
if target is None:
    return
account = account_for(target)
if account is None:
    print(f"{target.name} has no account to suspend.")
    return

hours = None
if raw is not None:
    try:
        hours = float(raw)
    except ValueError:
        print(f"Couldn't read a number of hours from {raw!r}.")
        return

try:
    suspend(account, hours=hours, reason=reason)
except Exception as err:  # pylint: disable=broad-exception-caught
    print(str(err))
    return

if hours is not None:
    print(f"Suspended {target.name} for {hours} hour(s).")
else:
    print(f"Suspended {target.name} indefinitely.")
