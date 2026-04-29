#!moo verb @keys --on $player

# pylint: disable=return-outside-function,undefined-variable

"""
List the SSH public keys registered for your account.

Usage:
    @keys

Displays a numbered list of your SSH keys showing the key type, fingerprint,
name, and when it was added. Use @add-key to add a key and @remove-key <n>
to remove one.
"""

from moo.sdk import context, list_ssh_keys

keys = list_ssh_keys(context.player)

if not keys:
    print("No SSH keys configured. Use @add-key to add one.")
else:
    print(f"SSH keys for {context.player.title()}:")
    for i, key in enumerate(keys, 1):
        name = key.name or "(unnamed)"
        print(f"  {i}. [{key.keytype}] {key.fingerprint}  {name}")
