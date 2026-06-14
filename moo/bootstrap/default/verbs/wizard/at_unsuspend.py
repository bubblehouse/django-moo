#!moo verb @unsuspend unsuspend_account --on $wizard --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
Staff command: lift a suspension, returning the account to active.
"""

from moo.sdk import context, account_for, unsuspend

if not context.parser.has_dobj_str():
    print("Usage: @unsuspend <player>")
    return

target = context.parser.get_dobj(lookup=True)
account = account_for(target)
if account is None:
    print(f"{target.name} has no account.")
    return

try:
    unsuspend(account)
except Exception as err:  # pylint: disable=broad-exception-caught
    print(str(err))
    return

print(f"Reinstated {target.name}.")
