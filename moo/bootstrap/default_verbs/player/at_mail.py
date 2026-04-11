#!moo verb @mail --on $player --dspec either

# pylint: disable=return-outside-function,undefined-variable

"""
Read and manage your mailbox.

Syntax:
    @mail               -- list your mailbox (10 messages per page)
    @mail page <n>      -- show page n of your mailbox
    @mail <n>           -- read message n (marks it read)
    @mail stats         -- show total, unread, and deleted counts
    @mail delete <n>    -- soft-delete message n
    @mail undelete <n>  -- restore a deleted message (n is 1-based among deleted)
"""

from moo.sdk import context, get_mailbox, get_message, mark_read, delete_message, undelete_message, count_unread, get_mail_stats, open_paginator, get_wrap_column

player = context.player
parser = context.parser

dobj_str = parser.get_dobj_str() if parser.has_dobj_str() else ""
parts = dobj_str.split() if dobj_str else []


PAGE_SIZE = 10


def show_mailbox(page=1):
    mailbox = get_mailbox(player)
    if not mailbox:
        print("Your mailbox is empty.")
        return
    unread = sum(1 for mr in mailbox if not mr.read)
    total = len(mailbox)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(1, min(page, total_pages))
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    page_slice = mailbox[start:end]
    TABLE_WIDTH = get_wrap_column()
    col_n = 4
    col_from = 18
    col_date = 12  # "Apr 10 20:06"
    col_subj = TABLE_WIDTH - col_n - col_from - col_date - 3 * 2  # 3 two-space gaps
    header = f"Your mailbox ({total} message{'s' if total != 1 else ''}, {unread} unread) \u2014 page {page} of {total_pages}:\n"
    sep = f"{'':>{col_n}}  {'From':<{col_from}}  {'Subject':<{col_subj}}  {'Date'}"
    divider = f"{'---':>{col_n}}  {'-' * col_from}  {'-' * col_subj}  {'-' * col_date}"
    rows = [header, sep, divider]
    for i, mr in enumerate(page_slice, start + 1):
        marker = "*" if not mr.read else " "
        sender_name = mr.message.sender.title() if mr.message.sender else "(deleted)"
        if len(sender_name) > col_from:
            sender_name = sender_name[:col_from - 1] + "\u2026"
        subject = mr.message.subject or "(no subject)"
        if len(subject) > col_subj:
            subject = subject[:col_subj - 1] + "\u2026"
        date_str = mr.sent_at.strftime("%b %d %H:%M") if mr.sent_at else "?"
        n_col = f"{i}{marker}"
        rows.append(f"{n_col:>{col_n}}  {sender_name:<{col_from}}  {subject:<{col_subj}}  {date_str}")
    rows.append("")
    footer = "* = unread   Type '@mail <n>' to read a message."
    if total_pages > 1:
        footer += "   '@mail page <n>' for other pages."
    rows.append(footer)
    open_paginator(player, "\n".join(rows))


def read_message(n):
    mr = get_message(player, n)
    if mr is None:
        print(f"There is no message {n}.")
        return
    sender_name = mr.message.sender.title() if mr.message.sender else "(deleted)"
    date_str = mr.sent_at.strftime("%b %d %H:%M") if mr.sent_at else "?"
    subject = mr.message.subject or "(no subject)"
    divider = "\u2500" * 45
    content = "\n".join([
        f"Message #{n} from {sender_name} \u2014 {date_str}",
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
elif len(parts) == 2 and parts[0] == "page" and parts[1].isdigit():
    show_mailbox(int(parts[1]))
elif parts == ["stats"]:
    show_stats()
elif len(parts) == 2 and parts[0] == "delete" and parts[1].isdigit():
    do_delete(int(parts[1]))
elif len(parts) == 2 and parts[0] == "undelete" and parts[1].isdigit():
    do_undelete(int(parts[1]))
elif len(parts) == 1 and parts[0].isdigit():
    read_message(int(parts[0]))
else:
    print("Usage: @mail | @mail page <n> | @mail <n> | @mail stats | @mail delete <n> | @mail undelete <n>")
