#!moo verb report --on $player --dspec any --ispec for:any

# pylint: disable=return-outside-function,undefined-variable

"""
Report abuse to the staff: ``report <player> for <reason>``, or ``report here
for <reason>`` about the room you are in. The report records the target's
account and your location in the audit log, and mails the staff list in
``gripe_recipients``. It works without the editor.
"""

from moo.sdk import NoSuchObjectError, NoSuchPropertyError, account_for, context, record_action, send_message

player = context.player
if not context.parser.has_dobj_str():
    print("Usage: report <player|here> for <reason>")
    return
# The reason is free text: take every word after the first "for", even words the parser reads as prepositions.
words = list(context.parser.words)
reason = " ".join(words[words.index("for") + 1 :]).strip() if "for" in words[1:] else ""
if not reason:
    print("Say what happened: report <player|here> for <reason>")
    return
# Staff read the report as console text; keep it plain and bounded.
reason = reason.replace("[", "(").replace("]", ")")[:1000]
if context.parser.get_dobj_str().strip().lower() == "here":
    target = player.location
else:
    try:
        target = context.parser.get_dobj(lookup=True)
    except NoSuchObjectError:
        target = None
if target is None:
    print("There is no one by that name here to report. Try `report here for <reason>`.")
    return
account = account_for(target)
reporter = account_for(player)
room = player.location
lines = [
    f"Reporter: {player.name}" + (f", account {reporter.pk}" if reporter is not None else ""),
    f"Target: #{target.pk} ({target.name})" + (f", account {account.pk}" if account is not None else ""),
    f"Room: #{room.pk} ({room.name})" if room is not None else "Room: none",
    f"Reason: {reason}",
]
detail = "\n".join(lines)
record_action("report", target=target, detail=detail)
try:
    recipients = _.gripe_recipients
except NoSuchPropertyError:
    recipients = []
if recipients:
    send_message(player, recipients, f"report about {target.name}", detail)
print("Thank you. The staff have your report.")
