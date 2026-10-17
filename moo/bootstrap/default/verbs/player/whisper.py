#!moo verb wh*isper --on $player --dspec any --ispec to:this

# pylint: disable=return-outside-function,undefined-variable

"""
Send secret messages between two players, as if they were whispering to each other. The way this
works is slightly the reverse of what might be expected, because the `whisper` verb on the person being whispered to is
the one that is invoked. The message — everything following the verb — is printed to the recipient, with suitable text
surrounding it to indicate that is it a whisper.
"""

from moo.sdk import account_for, context, is_muted, send_gmcp

if is_muted(account_for(context.player)):
    context.player.tell("You are muted.")
    return

source = context.player.title()
target = context.parser.get_pobj("to")
message = context.parser.get_dobj_str()
target.tell(f"{source} whispers to you: {message}")
context.player.tell(f"You whisper to {target.name}: {message}")

send_gmcp(target, "Comm.Channel.Text", {"channel": "whisper", "talker": context.player.name, "text": message})
