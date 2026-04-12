#!moo verb confunc --on $player

# pylint: disable=return-outside-function,undefined-variable

"""
Called when the player connects to the LambdaMOO server. It can be used to perform actions that should be
done every time the player logs in to the MUD. This is much the same idea as having a ~/.cshrc or ~/.kshrc file that is
activated when you log into a UN*X account. An example verb for the player class is listed below::

    $news:check(this);
    for x in this.messages:
      if x[1] > this.current_message:
        this:tell("You have new mail.  Type 'help mail' for info on reading it.");
        return;

This performs a couple of actions. First it calls `$news:check` to see whether the news has been updated since this
player last looked at it. Then it checks through the MOO Mail list on the player to see if any mail has arrived since
they were last connected.

You could place a variety of actions into this verb. For example, you may wish to tell your friends when you log in, by
sending a suitable message to them if they are connected. Similarly, you may wish to produce a special message in the
room you are in when you connect.
"""

from moo.sdk import context, count_unread

if not context.player.location:
    home = context.player.get_property("home") or _.player_start  # noqa: F821
    context.player.moveto(home)

context.player.location.look_self()

unread = count_unread(context.player)
if unread:
    suffix = "s" if unread != 1 else ""
    context.player.tell(f"You have {unread} unread message{suffix}. Type '@mail' to read.")
