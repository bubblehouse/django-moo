# SSH Key Management

DjangoMOO supports public-key authentication over SSH via the `simplesshkey` library. Three built-in verbs let players manage their own SSH keys without needing admin access.

## Commands

| Command | Effect |
|---------|--------|
| `@keys` | List your registered SSH public keys |
| `@add-key <key>` | Add an SSH public key to your account |
| `@remove-key <n>` | Remove the key at position `<n>` in the list |

## Listing Keys

```
@keys
```

Output:

```
SSH keys for Wizard:
  1. [ssh-ed25519] SHA256:abc123...  my laptop
  2. [ssh-rsa] SHA256:def456...  work machine
```

If no keys are registered, `@keys` prints:

```
No SSH keys configured. Use @add-key to add one.
```

## Adding a Key

Paste your public key as the direct object:

```
@add-key ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA... user@host
```

The key name is taken from the comment field (the last token in an OpenSSH public key). On success:

```
Added SSH key: [ssh-ed25519] SHA256:abc123...  user@host
```

Keys are validated against the OpenSSH format before saving. An invalid key string produces an error without creating any record.

If the key comment contains a word that the parser treats as a preposition — `for`, `at`, `by`, `in`, `on`, `from`, etc. — enclose the whole key in quotes:

```
@add-key "ssh-rsa AAAA... my key for work"
```

## Removing a Key

Use `@keys` to find the index, then pass it to `@remove-key`:

```
@keys
@remove-key 1
```

Output:

```
Removed SSH key: [ssh-ed25519] SHA256:abc123...  user@host
```

## How It Works

The verbs are implemented as wizard-owned verbs on `$player`. They call three SDK functions — `add_ssh_key`, `list_ssh_keys`, `remove_ssh_key` — defined in `moo/sdk.py`. Those functions access the `simplesshkey.UserKey` model directly; verb code in the sandbox cannot import `simplesshkey` itself.

Each player's SSH keys are stored as `UserKey` records linked to their Django `User` account. The SSH server in `moo/shell/server.py` validates keys during login via `validate_public_key`.

## Verb source files

- `moo/bootstrap/default_verbs/player/at_keys.py`
- `moo/bootstrap/default_verbs/player/at_add_key.py`
- `moo/bootstrap/default_verbs/player/at_remove_key.py`
