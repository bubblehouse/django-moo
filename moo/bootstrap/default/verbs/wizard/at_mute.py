#!moo verb @mute mute_account @unmute unmute_account --on $wizard --dspec any --ispec for:any

# pylint: disable=return-outside-function,undefined-variable

"""
Staff command: silence an account for everyone. ``@mute <player>`` is
open-ended; ``@mute <player> for <hours>`` sets a deadline. A muted account
keeps its login, but its say, emote, page, and whisper reach no one.
``@unmute <player>`` lifts the mute. Add ``because <reason>`` to either to
record why in the audit log. Keys to the account, and cannot target staff.
"""

from moo.sdk import context, account_for, mute, unmute

# This verb runs as its Wizard owner, so it checks the player who typed it.
if not context.player.is_wizard():
    print("Permission denied.")
    return

usage = (
    "Usage: @unmute <player> [because <reason>]"
    if "unmute" in verb_name
    else "Usage: @mute <player> [for <hours>] [because <reason>]"
)
if not context.parser.has_dobj_str():
    print(usage)
    return
target, raw, reason = _.wizard.sanction_args()
if target is None:
    return
account = account_for(target)
if account is None:
    print(f"{target.name} has no account.")
    return
if "unmute" in verb_name:
    try:
        unmute(account, reason=reason)
    except Exception as err:  # pylint: disable=broad-exception-caught
        print(str(err))
        return
    print(f"Unmuted {target.name}.")
    return
hours = None
if raw is not None:
    try:
        hours = float(raw)
    except ValueError:
        print(f"Couldn't read a number of hours from {raw!r}.")
        return
try:
    mute(account, hours=hours, reason=reason)
except Exception as err:  # pylint: disable=broad-exception-caught
    print(str(err))
    return
if hours is not None:
    print(f"Muted {target.name} for {hours} hour(s).")
else:
    print(f"Muted {target.name} until you unmute them.")
