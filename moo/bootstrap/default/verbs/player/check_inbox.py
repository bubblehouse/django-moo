#!moo verb check_inbox --on $player

# pylint: disable=return-outside-function,undefined-variable

"""
Print the first unread mail message in a human-readable format, then mark it as read.
Used by the moo-agent brain to inject prior-session context when a new token arrives.

Output format:
  [Mail] From <sender>: <body>      — when mail is present
  [Mail] No new messages.           — when mailbox is empty
"""

from moo.sdk import context, get_mailbox, mark_read

unread = [m for m in get_mailbox(context.player) if not m.read]
if unread:
    m = unread[0]
    sender_name = m.message.sender.name if m.message.sender else "unknown"
    body = m.message.body.replace("\n", " ")
    print(f"[Mail] From {sender_name}: {body}")
    mark_read(context.player, 1)
else:
    print("[Mail] No new messages.")
