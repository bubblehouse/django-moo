#!moo verb wh*isper --on $player --dspec any --ispec to:this

"""
Send secret messages between two players, as if they were whispering to each other. The way this
works is slightly the reverse of what might be expected, because the `whisper` verb on the person being whispered to is
the one that is invoked. The message — everything following the verb — is printed to the recipient, with suitable text
surrounding it to indicate that is it a whisper.
"""

from moo.sdk import context

source = context.player.title()
target = context.parser.get_pobj("to")
message = context.parser.get_dobj_str()
target.tell(f"{source} whispers to you: {message}")
context.player.tell(f"You whisper to {target.name}: {message}")
