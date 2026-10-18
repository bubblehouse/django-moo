#!moo verb @unsuspend unsuspend_account --on $wizard --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
Staff command: lift a suspension, returning the account to active. Add
``because <reason>`` to record why in the audit log.
"""

from moo.sdk import context, account_for, unsuspend

# This verb runs as its Wizard owner, so it checks the player who typed it.
if not context.player.is_wizard():
    print("Permission denied.")
    return

if not context.parser.has_dobj_str():
    print("Usage: @unsuspend <player> [because <reason>]")
    return

parsed = _.wizard.sanction_args()
target, reason = parsed[0], parsed[2]
if target is None:
    return
account = account_for(target)
if account is None:
    print(f"{target.name} has no account.")
    return

try:
    unsuspend(account, reason=reason)
except Exception as err:  # pylint: disable=broad-exception-caught
    print(str(err))
    return

print(f"Reinstated {target.name}.")
