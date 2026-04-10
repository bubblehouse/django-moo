#!moo verb @mail --on $player --dspec either

# pylint: disable=return-outside-function,undefined-variable

"""
Read and manage your mailbox.

Syntax:
    @mail               — list your mailbox
    @mail <n>           — read message n (marks it read)
    @mail stats         — show total, unread, and deleted counts
    @mail delete <n>    — soft-delete message n
    @mail undelete <n>  — restore a deleted message (n is 1-based among deleted)
"""

from moo.sdk import context, get_mailbox, get_message, mark_read, delete_message, undelete_message, count_unread, get_mail_stats, open_paginator

player = context.player
parser = context.parser

dobj_str = parser.get_dobj_str() if parser.has_dobj_str() else ""
parts = dobj_str.split() if dobj_str else []


def show_mailbox():
    mailbox = get_mailbox(player)
    if not mailbox:
        print("Your mailbox is empty.")
        return
    unread = 0
    for mr in mailbox:
        if not mr.read:
            unread += 1
    total = len(mailbox)
    header = f"Your mailbox ({total} message{'s' if total != 1 else ''}, {unread} unread):\n"
    col_n = 4
    col_from = 18
    col_subj = 34
    sep = f"{'':>{col_n}}  {'From':<{col_from}}  {'Subject':<{col_subj}}  {'Date'}"
    divider = f"{'---':>{col_n}}  {'----------------':<{col_from}}  {'------------------------------':<{col_subj}}  {'----------'}"
    rows = [header, sep, divider]
    for i, mr in enumerate(mailbox, 1):
        marker = "*" if not mr.read else " "
        sender_name = str(mr.message.sender) if mr.message.sender else "(deleted)"
        subject = mr.message.subject or "(no subject)"
        date_str = mr.sent_at.strftime("%b %d %H:%M") if mr.sent_at else "?"
        n_col = f"{i}{marker}"
        rows.append(f"{n_col:>{col_n}}  {sender_name:<{col_from}}  {subject:<{col_subj}}  {date_str}")
    rows.append("")
    rows.append("* = unread   Type '@mail <n>' to read a message.")
    open_paginator(player, "\n".join(rows))


def read_message(n):
    mr = get_message(player, n)
    if mr is None:
        print(f"There is no message {n}.")
        return
    sender_name = str(mr.message.sender) if mr.message.sender else "(deleted)"
    date_str = mr.sent_at.strftime("%b %d %H:%M") if mr.sent_at else "?"
    subject = mr.message.subject or "(no subject)"
    divider = "─" * 45
    content = "\n".join([
        f"Message #{n} from {sender_name} — {date_str}",
        f"Subject: {subject}",
        divider,
        mr.message.body,
    ])
    mark_read(player, n)
    open_paginator(player, content)


def show_stats():
    stats = get_mail_stats(player)
    print(f"Mail statistics: {stats['total']} total, {stats['unread']} unread, {stats['deleted']} deleted.")


def do_delete(n):
    if delete_message(player, n):
        print(f"Message {n} deleted.")
    else:
        print(f"There is no message {n}.")


def do_undelete(n):
    if undelete_message(player, n):
        print(f"Message {n} restored.")
    else:
        print(f"There is no deleted message {n}.")


if not parts:
    show_mailbox()
elif parts == ["stats"]:
    show_stats()
elif len(parts) == 2 and parts[0] == "delete" and parts[1].isdigit():
    do_delete(int(parts[1]))
elif len(parts) == 2 and parts[0] == "undelete" and parts[1].isdigit():
    do_undelete(int(parts[1]))
elif len(parts) == 1 and parts[0].isdigit():
    read_message(int(parts[0]))
else:
    print("Usage: @mail | @mail <n> | @mail stats | @mail delete <n> | @mail undelete <n>")
