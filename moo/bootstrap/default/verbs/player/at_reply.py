#!moo verb @reply at_reply_callback --on $player --dspec either

# pylint: disable=return-outside-function,undefined-variable

"""
Reply to a mail message.

Syntax:
    @reply <n>   — reply to message n in your mailbox

Opens the editor pre-filled with the original message body quoted (each line
prefixed with "> ") and a "Subject: Re: ..." header.  When saved, the reply
is sent to the original sender.
"""

from moo.sdk import context, open_editor, can_open_editor, lookup, get_message, send_message, NoSuchObjectError

if verb_name == "@reply":
    if not context.parser.has_dobj_str():
        print("[red]Reply to which message? Usage: @reply <n>[/red]")
        return

    dobj_str = context.parser.get_dobj_str()
    if not dobj_str.isdigit():
        print("[red]Usage: @reply <n>  (n is the message number)[/red]")
        return

    n = int(dobj_str)
    player = context.player
    mr = get_message(player, n)
    if mr is None:
        print(f"[red]There is no message {n}.[/red]")
        return

    if mr.message.sender is None:
        print("[red]The sender of that message no longer exists.[/red]")
        return

    original_subject = mr.message.subject or ""
    if original_subject.lower().startswith("re:"):
        new_subject = original_subject
    else:
        new_subject = f"Re: {original_subject}"

    if context.parser.has_pobj_str("with"):
        import re

        body = context.parser.get_pobj_str("with").replace("\\n", "\n")
        body = re.sub(r"\\([a-zA-Z_])", lambda m: "\n" + m.group(1), body).strip()
        if not body:
            print("[red]Message body is empty — nothing sent.[/red]")
            return
        send_message(context.player, [mr.message.sender], new_subject, body)
        print(f"[green]Reply sent to {mr.message.sender.title()}.[/green]")
        return

    if not can_open_editor():
        print(f'Raw mode: use `@reply {n} with "body"` to send inline.')
        print("Escape newlines as `\\n` in the with-string.")
        return

    quoted = "\n".join(f"> {line}" for line in mr.message.body.splitlines())
    initial = f"Subject: {new_subject}\n\n{quoted}\n\n"

    callback = player.get_verb("at_reply_callback")
    open_editor(
        player,
        initial,
        callback,
        mr.message.sender.pk,
        new_subject,
        content_type="text",
        title=f"Reply to {mr.message.sender.title()}",
    )

elif verb_name == "at_reply_callback":
    text = args[0]
    sender_pk = args[1]
    subject = args[2]
    recipient = lookup(sender_pk)

    lines = text.splitlines()
    if lines and lines[0].lower().startswith("subject:"):
        subject = lines[0][8:].strip() or subject
        body_lines = lines[1:]
        if body_lines and not body_lines[0].strip():
            body_lines = body_lines[1:]
        body = "\n".join(body_lines).strip()
    else:
        body = text.strip()

    if not body:
        print("[red]Message body is empty — nothing sent.[/red]")
        return

    send_message(context.player, [recipient], subject, body)
    print(f"[green]Reply sent to {recipient.title()}.[/green]")
