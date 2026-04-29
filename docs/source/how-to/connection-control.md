# Connection Control Verbs

DjangoMOO provides a set of built-in verbs that automation clients can use to make output machine-readable. They are defined on `$player` and are available to all connected players.

For accessibility-focused settings (screen-reader markers, textual severity prefixes, quiet mode, MUD client compatibility), see {doc}`accessibility`.

## PREFIX and SUFFIX

`PREFIX` and `SUFFIX` wrap each command's output in marker strings. An automation client sets unique markers, sends commands, and detects the end of each response by watching for the suffix rather than relying on timeouts or prompt detection.

```
>>> PREFIX >>MOO-START<<
Output prefix set to: >>MOO-START<<
>>> SUFFIX >>MOO-END<<
>>MOO-START<<
Output suffix set to: >>MOO-END<<
>>> look
```

Output:

```
>>MOO-START<<
The Laboratory
A cavernous laboratory filled with gadgetry of every kind,
this seems like a dumping ground for every piece of dusty forgotten
equipment a mad scientist might require.

You see a heavy wooden workbench here.
Newman, Cliff, and Player are here.
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

## OUTPUTPREFIX and OUTPUTSUFFIX

`OUTPUTPREFIX` and `OUTPUTSUFFIX` wrap *all* output sent to the client — including asynchronous messages from other players (via `tell()`) — not just responses to commands. They complement `PREFIX`/`SUFFIX`, which only frame command output.

```
>>> OUTPUTPREFIX ===
Global output prefix set to: ===
>>> OUTPUTSUFFIX ===
===
Global output suffix set to: ===
>>> look
===
The Laboratory
A cavernous laboratory filled with gadgetry of every kind,
this seems like a dumping ground for every piece of dusty forgotten
equipment a mad scientist might require.

You see a heavy wooden workbench here.
Newman, Cliff, and Player are here.
===
```

If both layers are active, the global markers are outermost:

```
===           ← OUTPUTPREFIX
>>START<<     ← PREFIX (if set)
...output...
>>END<<       ← SUFFIX (if set)
===           ← OUTPUTSUFFIX
```

An async `tell()` from another player will also be wrapped:

```
===
Wizard pages: "hello"
===
```

**Syntax**:

| Command | Effect |
|---------|--------|
| `OUTPUTPREFIX <marker>` | Emit `<marker>` before all output |
| `OUTPUTPREFIX` | Show the current global prefix |
| `OUTPUTPREFIX clear` | Remove the global prefix |
| `OUTPUTSUFFIX <marker>` | Emit `<marker>` after all output |
| `OUTPUTSUFFIX` | Show the current global suffix |
| `OUTPUTSUFFIX clear` | Remove the global suffix |

Both markers are session-specific and cleared on disconnect.

## .flush

`.flush` drains the pending async output queue immediately. Any `tell()` messages or system notices that have accumulated since the last poll cycle are written to the terminal right now, before the next command is sent.

```
.flush
```

This is especially useful in automation scripts: sending `.flush` before each command ensures that async background output (such as `confunc`/`disfunc` messages from earlier build steps) does not intermix with the next command's response.

`.flush` is a connection-level command — it is not dispatched through the verb parser and does not require any verb to be defined.

## a11y quiet

Clean plain-text output — no ANSI colour, bare `$` prompt — is controlled by the `a11y` verb:

```
>>> a11y quiet on
quiet on
>>> look
The Laboratory
A cavernous laboratory filled with gadgetry of every kind,
    this seems like a dumping ground for every piece of dusty forgotten
    equipment a mad scientist might require.

You see a heavy wooden workbench here.
Newman, Cliff, and Player are here.
```

See {doc}`accessibility` for the full `a11y` verb reference. The earlier
`QUIET enable` / `QUIET disable` command has been removed — use
`a11y quiet on` / `a11y quiet off` instead.

## Automation Mode

The `MooSSH` automation client in `extras/skills/game-designer/tools/moo_ssh.py` wires the common setup into a single helper:

```python
with MooSSH() as moo:
    moo.enable_automation_mode()   # PREFIX + SUFFIX + a11y quiet on
    output = moo.run("look")       # delimiter-based; ~1.1s per command
```

Without automation mode, each command waits for a fixed timeout (~6s). With delimiters active, `run()` returns as soon as the suffix marker appears.

## Connection Lifecycle Callbacks

When objects move and when players connect or disconnect, DjangoMOO calls a set
of callback verbs. These are the hooks to override when you want custom behavior
on a room or player subclass.

### Movement callbacks

These fire automatically inside `object.py` whenever any object's location
changes via `moveto()`. They are not limited to players.

| Verb | `this` | Argument | Default behavior |
|------|--------|----------|-----------------|
| `$room.enterfunc` | destination room | arriving object (`args[1]`) | shows `look_self` to players; clears `blessed_object` |
| `$room.exitfunc` | source room | departing object (`args[1]`) | clears `seated_on` property |

### Connection callbacks

These fire when a player's SSH session starts or ends. The call order follows
the original LambdaMOO convention.

In all four tables below, `context.player` is the player whose session is
starting or ending. `this` is the object the verb is dispatched on.

**On connect** (`player.confunc` → `player.location.confunc`):

| Verb | `this` | Default behavior |
|------|--------|------------------|
| `$player.confunc` | the player | moves player to their `home` (or `_.player_start`) if they have no location, prints unread mail count, sends GMCP `Char.Name` and `Room.Info` events |
| `$room.confunc` | the player's room | calls `look_self`, announces "has connected" |

**On disconnect** (`player.location.disfunc` → `player.disfunc`):

| Verb | `this` | Default behavior |
|------|--------|------------------|
| `$room.disfunc` | the player's room | moves player home (if not already there), announces "has disconnected" |
| `$player.disfunc` | the player | no-op stub |

`$player.disfunc` is an intentional no-op on the base class — override it
on a player subclass to add logout behavior such as notifying friends.
`$player.confunc` already does the standard login chores listed above; if
you override it on a subclass, call `passthrough()` first (or replicate
those chores) so mail counts and GMCP events still fire.

The connect callbacks run as Celery tasks, but the SSH session waits for them
to complete before showing the first prompt. This means `look_self` output
(and any other `print()` calls in `confunc` verbs) appears above the first
prompt, not interleaved with it. Disconnect callbacks are fire-and-forget.

## Implementation Notes

Session settings cross the Celery / SSH server process boundary via the Kombu message queue — the same mechanism used by the text editor and paginator. `set_session_setting()` in `moo/sdk/output.py` publishes a `{"event": "session_setting", ...}` message; the SSH server's `process_messages()` loop applies it to the connection's own registry.

See `moo/bootstrap/default_verbs/player/PREFIX.py`, `SUFFIX.py`, `OUTPUTPREFIX.py`, `OUTPUTSUFFIX.py`, `a11y.py`, and `WRAP.py` for the verb implementations. `.flush` is handled directly in `moo/shell/prompt.py` (`process_commands` and `_drain_messages`).
