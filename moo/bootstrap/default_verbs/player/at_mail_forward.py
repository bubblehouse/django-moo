#!moo verb @forward at_forward_callback --on $player --dspec any --ispec to:any

# pylint: disable=return-outside-function,undefined-variable

"""
Forward a mail message to another player.

Syntax:
    @forward <n> to <player>   — forward message n to the named player

Opens the editor pre-filled with the forwarded body and a "Fwd: " subject
prefix.  When saved, the message is sent to the target player.
"""

from moo.sdk import context, open_editor, lookup, get_message, send_message, NoSuchObjectError

if verb_name == "@forward":
    parser = context.parser

    if not parser.has_dobj_str():
        print("[red]Forward which message? Usage: @forward <n> to <player>[/red]")
        return
    if not parser.has_pobj_str("to"):
        print("[red]Forward to whom? Usage: @forward <n> to <player>[/red]")
        return

    dobj_str = parser.get_dobj_str()
    if not dobj_str.isdigit():
        print("[red]Usage: @forward <n> to <player>  (n is the message number)[/red]")
        return

    n = int(dobj_str)
    player = context.player
    mr = get_message(player, n)
    if mr is None:
        print(f"[red]There is no message {n}.[/red]")
        return

    try:
        recipient = parser.get_pobj("to", lookup=True)
    except NoSuchObjectError:
        print(f"[red]I don't see '{parser.get_pobj_str('to')}' here.[/red]")
        return

    player_class = lookup("Generic Player")
    if not recipient.is_a(player_class):
        print(f"[red]{recipient} is not a player.[/red]")
        return

    original_subject = mr.message.subject or ""
    if original_subject.lower().startswith("fwd:"):
        new_subject = original_subject
    else:
        new_subject = f"Fwd: {original_subject}"

    sender_name = str(mr.message.sender) if mr.message.sender else "(deleted)"
    date_str = mr.sent_at.strftime("%b %d %H:%M") if mr.sent_at else "?"
    fwd_header = f"---------- Forwarded message ----------\nFrom: {sender_name}\nDate: {date_str}\nSubject: {original_subject}\n\n"
    initial = f"Subject: {new_subject}\n\n{fwd_header}{mr.message.body}\n"

    callback = player.get_verb("at_forward_callback")
    open_editor(
        player,
        initial,
        callback,
        recipient.pk,
        new_subject,
        content_type="text",
        title=f"Forward to {recipient}",
    )

elif verb_name == "at_forward_callback":
    text = args[0]
    recip_pk = args[1]
    subject = args[2]
    recipient = lookup(recip_pk)

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
    print(f"[green]Message forwarded to {recipient}.[/green]")
