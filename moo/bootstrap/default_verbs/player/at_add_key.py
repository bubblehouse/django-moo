#!moo verb @add-key --on $player --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
Add an SSH public key to your account for public-key authentication.

Usage:
    @add-key <public-key>

The key string should be in OpenSSH format, e.g.:
    @add-key ssh-ed25519 AAAA... user@host

If the key comment contains a preposition (for, at, by, in, etc.), enclose
the whole key in quotes:
    @add-key "ssh-rsa AAAA... my key for work"

The key name is taken from the comment field automatically. Use @keys to
list your keys and @remove-key <n> to remove one.
"""

from moo.sdk import context, add_ssh_key, UsageError

key_string = context.parser.get_dobj_str()
if not key_string:
    raise UsageError("Usage: @add-key <public-key>")

key = add_ssh_key(context.player, key_string)
name = key.name or "(unnamed)"
print(f"Added SSH key: [{key.keytype}] {key.fingerprint}  {name}")
