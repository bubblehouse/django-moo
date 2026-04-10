#!moo verb @gripe at_gripe_callback --on $player

# pylint: disable=return-outside-function,undefined-variable

"""
Send a complaint or observation to the MOO administrators.

Syntax:
    @gripe   — open editor to write your gripe

The gripe is sent as a mail message to all players listed in the
``gripe_recipients`` system property.  The subject is auto-filled as
"@gripe from <player>".  Body text is entered via the editor.
"""

from moo.sdk import context, open_editor, send_message, NoSuchPropertyError

if verb_name == "@gripe":
    player = context.player
    try:
        recipients = _.gripe_recipients  # noqa: F821 — _ is the system object in verb scope
    except NoSuchPropertyError:
        print("[red]gripe_recipients is not configured. Contact an administrator.[/red]")
        return

    if not recipients:
        print("[red]No gripe recipients are configured. Contact an administrator.[/red]")
        return

    subject = f"@gripe from {player}"
    callback = player.get_verb("at_gripe_callback")
    open_editor(
        player,
        "",
        callback,
        [r.pk for r in recipients],
        subject,
        content_type="text",
        title="Send a gripe to the administrators",
    )

elif verb_name == "at_gripe_callback":
    text = args[0]
    recip_pks = args[1]
    subject = args[2]

    if not text.strip():
        print("[red]Gripe body is empty — nothing sent.[/red]")
        return

    from moo.sdk import lookup
    recipients = [lookup(pk) for pk in recip_pks]
    send_message(context.player, recipients, subject, text.strip())
    print("[green]Your gripe has been sent to the administrators.[/green]")
