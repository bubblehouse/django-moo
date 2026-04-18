#!moo verb @remove-key --on $builder --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
Remove an SSH public key from your account by its list index.

Usage:
    @remove-key <n>

Use @keys to see the numbered list of your current SSH keys, then pass the
index number to remove the corresponding key.

Example:
    @keys
    @remove-key 1
"""

from moo.sdk import context, remove_ssh_key, UsageError

index_str = context.parser.get_dobj_str()
if not index_str:
    raise UsageError("Usage: @remove-key <n>")

try:
    index = int(index_str)
except Exception as exc:
    raise UsageError(f"'{index_str}' is not a valid index. Usage: @remove-key <n>") from exc

key = remove_ssh_key(context.player, index)
name = key.name or "(unnamed)"
print(f"Removed SSH key: [{key.keytype}] {key.fingerprint}  {name}")
