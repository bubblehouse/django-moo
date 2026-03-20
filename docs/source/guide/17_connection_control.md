# Connection Control Verbs

DjangoMOO provides three built-in verbs that automation clients can use to make output machine-readable. They are defined on `$player` and are available to all connected players.

## PREFIX and SUFFIX

`PREFIX` and `SUFFIX` wrap each command's output in marker strings. An automation client sets unique markers, sends commands, and detects the end of each response by watching for the suffix rather than relying on timeouts or prompt detection.

```
PREFIX >>MOO-START<<
SUFFIX >>MOO-END<<
look
```

Output:

```
>>MOO-START<<
The Laboratory(#3)
You see nothing special.
>>MOO-END<<
```

**Syntax**:

| Command | Effect |
|---------|--------|
| `PREFIX <marker>` | Emit `<marker>` before each command's output |
| `PREFIX` | Show the current prefix |
| `PREFIX clear` | Remove the prefix |
| `SUFFIX <marker>` | Emit `<marker>` after each command's output |
| `SUFFIX` | Show the current suffix |
| `SUFFIX clear` | Remove the suffix |

Both markers are session-specific and are cleared when the player disconnects.

## QUIET

`QUIET` disables Rich color markup in command output and simplifies the prompt to a bare `$ `. This removes ANSI escape sequences so automation clients receive clean plain text.

```
QUIET enable
look
The Laboratory(#3)
You see nothing special.
$
```

**Syntax**:

| Command | Effect |
|---------|--------|
| `QUIET enable` | Enable quiet mode |
| `QUIET disable` | Disable quiet mode |
| `QUIET` | Show current setting |

Note: `enable` / `disable` are used rather than `on` / `off` because `on` and `off` are MOO prepositions and would not be parsed as a direct object.

## Automation Mode

The `MooSSH` automation client in `extras/skills/game-designer/tools/moo_ssh.py` calls all three in a single helper:

```python
with MooSSH() as moo:
    moo.enable_automation_mode()   # PREFIX + SUFFIX + QUIET enable
    output = moo.run("look")       # delimiter-based; ~1.1s per command
```

Without automation mode, each command waits for a fixed timeout (~6s). With delimiters active, `run()` returns as soon as the suffix marker appears.

## Implementation Notes

Session settings cross the Celery / SSH server process boundary via the Kombu message queue — the same mechanism used by the text editor and paginator. `set_session_setting()` in `moo/sdk.py` publishes a `{"event": "session_setting", ...}` message; the SSH server's `process_messages()` loop applies it to the connection's own registry.

See `moo/bootstrap/default_verbs/player/PREFIX.py`, `SUFFIX.py`, and `QUIET.py` for the verb implementations.
