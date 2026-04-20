#!moo verb @password at_password_got_old at_password_got_new at_password_confirm --on $player

# pylint: disable=return-outside-function,undefined-variable

"""
Change the player's password interactively.

Usage: @password

Prompts for the current password, then the new password twice for confirmation.
Wizards may leave the old-password prompt blank to perform an administrative reset.
"""

from moo.sdk import context, open_input, set_password

if verb_name == "@password":
    player = context.player
    callback = this.get_verb("at_password_got_old")
    open_input(player, "Old password: ", callback, password=True)

elif verb_name == "at_password_got_old":
    old_pw = args[0]
    player = context.player
    callback = this.get_verb("at_password_got_new")
    open_input(player, "New password: ", callback, old_pw, password=True)

elif verb_name == "at_password_got_new":
    new_pw = args[0]
    old_pw = args[1]
    player = context.player
    callback = this.get_verb("at_password_confirm")
    open_input(player, "Confirm new password: ", callback, old_pw, new_pw, password=True)

elif verb_name == "at_password_confirm":
    confirm_pw = args[0]
    old_pw = args[1]
    new_pw = args[2]
    if confirm_pw != new_pw:
        print("[red]Passwords do not match.[/red]")
        return
    set_password(context.player, new_pw, old_pw or None)
    print("Password changed.")
