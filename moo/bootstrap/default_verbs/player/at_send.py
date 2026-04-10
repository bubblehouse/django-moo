#!moo verb @send at_send_callback --on $player --dspec either

# pylint: disable=return-outside-function,undefined-variable

"""
Send a mail message to another player.

Syntax:
    @send <player>   — open editor to compose; first line becomes the subject

The editor opens pre-filled with a "Subject: " prompt on the first line.
When saved, the first line (stripped of the "Subject: " prefix) becomes the
subject; all remaining lines become the body.
"""

from moo.sdk import context, open_editor, lookup, send_message, NoSuchObjectError

if verb_name == "@send":
    if not context.parser.has_dobj_str():
        print("[red]Send to whom? Usage: @send <player>[/red]")
        return

    try:
        recipient = context.parser.get_dobj(lookup=True)
    except NoSuchObjectError:
        print(f"[red]I don't see '{context.parser.get_dobj_str()}' here.[/red]")
        return

    player_class = lookup("Generic Player")
    if not recipient.is_a(player_class):
        print(f"[red]{recipient} is not a player.[/red]")
        return

    callback = context.player.get_verb("at_send_callback")
    initial = "Subject: \n\n"
    open_editor(
        context.player,
        initial,
        callback,
        recipient.pk,
        content_type="text",
        title=f"Message to {recipient}",
    )

elif verb_name == "at_send_callback":
    text = args[0]
    recip_pk = args[1]
    recipient = lookup(recip_pk)

    lines = text.splitlines()
    if lines and lines[0].lower().startswith("subject:"):
        subject = lines[0][8:].strip() or "(no subject)"
        # Skip the blank separator line after the subject header if present
        body_lines = lines[1:]
        if body_lines and not body_lines[0].strip():
            body_lines = body_lines[1:]
        body = "\n".join(body_lines).strip()
    else:
        subject = "(no subject)"
        body = text.strip()

    if not body:
        print("[red]Message body is empty — nothing sent.[/red]")
        return

    send_message(context.player, [recipient], subject, body)
    print(f"[green]Message sent to {recipient}.[/green]")
