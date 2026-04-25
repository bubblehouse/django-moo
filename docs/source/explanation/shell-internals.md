# Inside the Shell Client

The DjangoMOO shell (`moo/shell/`) is the SSH front-end that every connected
player talks to. It looks like a conventional prompt — name, location, dollar
sign — but under the hood it coordinates an AsyncSSH channel, a prompt_toolkit
application, a Kombu consumer, two concurrent asyncio coroutines, and a
registry of per-session settings that travels through the Django cache so that
Celery workers can see it.

This document explains *why* the client is shaped the way it is. For the
player-facing commands (`PREFIX`, `.flush`, etc.) see
{doc}`../how-to/connection-control`. For accessibility settings and the
`a11y` verb, see {doc}`../how-to/accessibility`. For the verbs that
`confunc` / `disfunc` dispatch into, see {doc}`../reference/verbs`.

## Architecture at a Glance

```
       ┌──────────────────────────────────────────────────────────┐
       │  AsyncSSH server (moo/shell/server.py)                   │
       │  - listens on port 8022                                  │
       │  - dispatches each session to MooPromptToolkitSSHSession │
       │  - that session calls interact() → embed()               │
       └──────────────────────────────────────────────────────────┘
                               │
                   per-session │
                               ▼
       ┌──────────────────────────────────────────────────────────┐
       │  MooPrompt (moo/shell/prompt.py)                         │
       │                                                          │
       │  ┌───────────────────────┐    ┌──────────────────────┐   │
       │  │ process_commands      │    │ process_messages     │   │
       │  │ - renders the prompt  │    │ - drains Kombu       │   │
       │  │ - awaits user input   │    │ - writes async tells │   │
       │  │ - awaits editor /     │    │ - routes editor /    │   │
       │  │   paginator / input   │    │   paginator events   │   │
       │  │   events via queues   │    │   to queues          │   │
       │  └─────────┬─────────────┘    └──────────┬───────────┘   │
       │            └──── asyncio.Queue ──────────┘               │
       └──────────────────────────────────────────────────────────┘
                               │
                               ▼
       ┌──────────────────────────────────────────────────────────┐
       │  Kombu broker (Redis / RabbitMQ)                         │
       │  - messages.<user_pk> queue, auto_delete=True            │
       │  - published by verb code via moo.sdk.output.write       │
       │  - consumed by the session buffer opened in _repl_setup  │
       └──────────────────────────────────────────────────────────┘
                               ▲
                               │
       ┌──────────────────────────────────────────────────────────┐
       │  Celery workers running verb code                        │
       │  - print() / tell() → broker → this session's queue      │
       │  - read session settings via Django cache mirror         │
       └──────────────────────────────────────────────────────────┘
```

Two coroutines run for the lifetime of a session:

- `process_commands` owns the SSH channel's output and drives the input loop.
- `process_messages` owns the Kombu consumer and feeds async output back to
  the user.

They communicate through `asyncio.Event` flags, four `asyncio.Queue` instances
(editor / paginator / input_prompt / disconnect), and a shared
`_pending_connect_output` string for the startup burst.

## The Three Modes

The session's mode is chosen in `MooPromptToolkitSSHSession.session_started`
by inspecting the SSH client's `TERM` environment variable:

| TERM contains            | Mode              | Purpose                                   |
|--------------------------|-------------------|-------------------------------------------|
| `moo-automation`         | `rich` + `is_automation=True` | machine-driven clients; CPR disabled, prompt shortcuts off |
| `xterm-256-basic` (exact)| `raw`             | traditional MUD clients; no cursor control, line-based I/O |
| anything else            | `rich`            | default prompt_toolkit TUI                 |

The mode is propagated to `MooPrompt.__init__` and also mirrored into the
Django cache (`moo:session:<user_pk>:mode`) so out-of-process Celery verbs
can read it via `moo.sdk.get_client_mode()`.

### Rich mode

A full prompt_toolkit `Application` drives the screen. Commands, async tells,
editor/paginator TUIs, and input prompts all coexist because prompt_toolkit's
`run_in_terminal` can temporarily suspend the input line, print something
above it, and restore it.

### Raw mode

For classic MUD clients that cannot tolerate cursor manipulation. No
prompt_toolkit `Application` is instantiated; the prompt is written to the
asyncssh channel once per turn via `_chan_write`, and line input is read by
`_read_line_raw` directly. Async tells simply print above the next prompt —
the traditional MUD experience.

Escape sequences (anything starting with `\x1b`) are discarded by the raw
reader on purpose. MUD clients do their own line editing and history; the
server-side reader is a plain byte buffer.

### Automation mode

A variant of rich mode where interactive shortcuts (`"` → `say "%"`, etc.) are
suppressed and CPR (cursor position report) queries are disabled. Used by
`MooSSH` in `extras/skills/game-designer/tools/moo_ssh.py` and by the agent
runtime. Editor TUIs are rejected with an error that points at the inline
`@edit … with "…"` form; paginator events are inlined directly rather than
queued for a TUI.

## The Kombu Message Bus

Every connected session has a dedicated queue named `messages.<user_pk>`,
bound to the `moo` direct exchange on routing key `user-<user_pk>`. The queue
is declared with `auto_delete=True` — RabbitMQ / Redis deletes it as soon as
the last consumer disconnects.

### Single-consumer invariant

Opening and closing the consumer on demand causes two subtle failures:

1. **Lost confunc output.** If the queue is declared only at drain time, any
   `tell()` published between task dispatch and drain start is dropped at the
   exchange — no matching queue exists to route it into.
2. **Zombie splitting.** If a previous session's consumer is still attached
   (because `prompt_async` hung on a dead channel), a new connection adds a
   *second* consumer and the broker round-robin-splits messages between them.

The fix lives in `_open_session_buffer`: one `SimpleBuffer` is opened in
`_repl_setup` *before* confunc fires, held for the lifetime of the session,
and closed in `_repl_teardown` (with a final safety close in `embed`'s
`finally` block). All three readers — the startup coalescer, the `.flush`
command, and the `process_messages` loop — go through the same buffer via
the `@sync_to_async`-wrapped `_drain_session_buffer`, which serializes
access so there are no racing `get_nowait` calls.

### Message shapes

Three kinds of things arrive on the queue:

- **Strings** — plain Rich-markup text from `print()` / `tell()`, printed
  directly.
- **Dicts with an `event` key** — structured events. The supported kinds are
  `editor`, `paginator`, `input_prompt`, `session_setting`, and `disconnect`.
- **Anything else** — never produced in practice; logged and ignored.

`session_setting` events update `_session_settings[user_pk]` in-place.
Everything else is routed by `_route_event` to its matching asyncio queue
(or, for `paginator` in raw / automation mode, inlined directly).

## Startup Choreography

`_repl_setup` is responsible for making sure the first prompt lands in the
right place, with the right colour, below any `look_self` burst from
`confunc`. The sequence is:

1. Wipe stale `_session_settings[user_pk]` (previous connection on the same
   account might have left `a11y quiet` / `PREFIX` state behind) and re-stamp
   `mode` / `automation`.
2. Mirror `mode` into the Django cache so Celery workers see it.
3. Set `moo:connected:<user_pk>` so `is_connected()` returns `True` by the
   time the room's confunc fires.
4. Open the Kombu session buffer.
5. Dispatch `player.confunc` and `player.location.confunc` as Celery tasks
   and wait on the result backend (with `propagate=False` so a broken
   confunc can't take down the prompt).
6. Coalesce the confunc burst by polling the buffer until it has been empty
   for three consecutive passes (Redis round-trip latency can split one
   verb's `tell()` burst across multiple reads).
7. Render all coalesced pieces through Rich into a single ANSI blob and stash
   it in `self._pending_connect_output`.
8. Set `startup_drain_complete`.

`process_messages` waits on both `startup_drain_complete` and
`prompt_app_ready` before it starts consuming. Without that gate, the loop
could write via `print_formatted_text` before the `Application` is live — at
which point prompt_toolkit's default `AppSession` has no wired output and
the bytes are dropped on the floor.

### Handing off the confunc burst

Writing the burst directly to the SSH channel (bypassing prompt_toolkit)
works, but it races the `Application`'s CPR query and produces a spurious
"your terminal doesn't support CPR" warning even on iTerm.

The client instead sends the buffer through the `Application`'s own output
pipeline. `_make_osc_pre_run` returns a `pre_run` callback that, just before
the first render, calls `app.output.write_raw(self._pending_connect_output)`
and clears the buffer. The prompt's geometry then lands below the confunc
output with the CPR state correct.

Raw mode has no `Application` — it consumes the buffer via `_chan_write` at
the top of `process_commands_raw` and signals `prompt_app_ready` manually
so `process_messages` can proceed.

## OSC 133 Semantic Shell Integration

DjangoMOO emits OSC 133 markers so screen readers and modern terminals can
navigate command-by-command. See {doc}`../how-to/connection-control` for the
player-facing toggle; the mechanics are:

| Marker | Meaning                       |
|--------|-------------------------------|
| `ESC]133;A`  | prompt start            |
| `ESC]133;B`  | command start (end of prompt) |
| `ESC]133;C`  | output start            |
| `ESC]133;D;<status>` | command end with exit status |

### Why not bake `;A`/`;B` into the prompt's FormattedText?

That was the first approach. It breaks in a subtle way: `run_in_terminal`
redraws the prompt after every async tell, and each redraw re-emits the
markers — so a burst of N async lines looks like N separate commands to a
screen reader.

The current approach in rich mode emits the markers from prompt_toolkit's
render events (`before_render` / `after_render`) rather than from the
prompt content, and gates them on a single-entry list
`self._osc_needs_markers = [True]`:

- Set `True` at the start of each input cycle.
- `before_render` writes `;A` if the flag is set, `after_render` writes `;B`
  and flips the flag to `False`.
- `_run_in_terminal_marked` wraps every `run_in_terminal` call that emits
  visible output and flips the flag back to `True` on exit — so the next
  render (which lands at a new screen position) gets a fresh pair of
  markers.
- Keystroke-driven redraws at the same screen position skip emission.

Raw mode has no render events, so it injects `;A`/`;B` around the prompt
string literally in `process_commands_raw`, then `;C` and `;D` around
command output.

The `_RawAnsi(str)` marker class exists so `writer` can tell OSC passthrough
apart from ordinary Rich markup: Rich would escape the `\x1b]133;…\x07`
bytes, and prompt_toolkit's ANSI parser silently mangles the OSC introducer.
`_RawAnsi` values are written via `[ZeroWidthEscape]` in rich mode and
straight to the channel in raw mode.

## Events and Queues

Verbs can publish three kinds of structured events that need a full-screen
or inline interruption of the REPL:

| Event         | Handler                    | Purpose                                       |
|---------------|----------------------------|-----------------------------------------------|
| `editor`      | `run_editor_session`       | full-screen text editor (prompt_toolkit TUI)  |
| `paginator`   | `run_paginator_session`    | full-screen read-only pager (pypager)         |
| `input_prompt`| `run_input_session`        | inline prompt for a single value              |

All three events land on the Kombu queue, are routed to their dedicated
`asyncio.Queue` by `_route_event`, and are picked up by `process_commands`
via `asyncio.wait(..., return_when=FIRST_COMPLETED)` racing the user-input
task.

### Direct dispatch after command completion

When `handle_command` finishes, any events the verb published are returned
alongside the output string. `_dispatch_pending_event` waits up to two
seconds for each event to surface on the matching queue and invokes the
handler directly, bypassing the prompt_async race.

This matters for multi-stage flows like `@password`: without direct
dispatch the MOO prompt would flash for a frame between the verb and the
input prompt it just spawned.

### Callback wiring

Editor and input events carry a `callback_this_id` + `callback_verb_name`
pair; when the user saves the edit or submits the input, the handler calls
`tasks.invoke_verb.delay` with the result as the first positional arg. A
wizard check (`caller.is_wizard()`) guards the callback path — only verbs
that run as a wizard are allowed to register callbacks, because the
callback shell runs outside the verb sandbox.

## Session Settings

`_session_settings` is a process-local dict keyed by Django user PK.
Everything the shell cares about per-session lives there: `mode`,
`automation`, `quiet_mode`, `output_prefix`, `output_suffix`,
`output_global_prefix`, `output_global_suffix`, `color_system`,
`terminal_width`, `osc133_mode`, `prefixes_mode`.

Verbs running in Celery are in a different process, so they can't read this
dict directly. The pattern is:

- **Writes from verb code** → `moo.sdk.output.set_session_setting` publishes a
  `{"event": "session_setting", ...}` message on the player's Kombu queue.
  `process_messages` (or the startup drain) applies it to the in-process
  dict.
- **Writes from verb code that Celery itself needs to read** (e.g. `mode`,
  `quiet_mode`, `terminal_width`) → also mirrored into the Django cache so
  `moo.sdk.get_session_setting` can read them cross-process.

The mirror is one-way: the SSH session is the source of truth for the
dict, the cache is a convenience for workers. Both are cleared in
`_repl_teardown` so a stale state from a crashed session cannot leak into
a new one.

## Teardown

When either coroutine exits, the other must exit too — otherwise the Kombu
consumer stays attached and any future connection for the same user
round-robin-splits messages with the zombie.

`embed` enforces this with `asyncio.wait(..., return_when=FIRST_COMPLETED)`
followed by a `finally` block that:

1. Sets `is_exiting` and `disconnect_event`.
2. Cancels the still-pending task.
3. `await`s both with `return_exceptions=True` so teardown propagates.
4. Calls `_close_session_buffer` as a final safety — if a task was
   cancelled before `_repl_teardown` could run, this still releases the
   consumer.

`process_messages` also polls `self._chan.is_closing()` on every iteration.
asyncssh does not always surface channel close to prompt_toolkit; without
this poll, `prompt_async` can hang indefinitely on a dead channel.

## The `.flush` Command

`.flush` is intercepted by `process_commands` before dispatch. It calls
`_drain_messages` (which shares the session buffer with `process_messages`)
and writes the resulting pieces via `_run_in_terminal_marked`. Events
encountered during the drain are routed to their queues as normal, so
editor / paginator state stays consistent even when the user explicitly
asks to flush.

This is the escape hatch for automation clients that want a clean boundary
between the confunc burst and the response to the next command.

## Editor and Paginator TUIs

`moo/shell/editor.py` and `moo/shell/paginator.py` are thin wrappers around
prompt_toolkit and pypager respectively. Both accept a `content_type` of
`"python"`, `"json"`, or `"text"` and load a Pygments lexer lazily — the
lexer module is imported only when its content type is requested, so
starting a session does not pay the cost of every supported lexer.

The editor's confirmation flow uses a `state = {"confirming": None}` dict
and two `Condition` filters so that Ctrl-S and Ctrl-C first prompt for
yes/no confirmation rather than exiting immediately. The paginator disables
a small set of pypager commands (`_print_filename`, `_examine`, etc.) that
would expose filesystem operations to players.

## AsyncSSH Server

`moo/shell/server.py` is the entrypoint launched by the `runshell` Django
management command. Key choices:

- `line_editor=False` in `create_server`. asyncssh's built-in line editor
  wraps all output through `SSHLineEditor.process_output()`, which does a
  second LF→CRLF translation and injects `' \b'` at column-80 boundaries.
  That corrupts prompt_toolkit's TUI output and is incompatible with a
  full-screen application. prompt_toolkit does all the line editing we
  need; asyncssh's layer must be disabled.
- `keepalive_interval=15`, `keepalive_count_max=3`. asyncssh will close
  channels that miss 3×15s of keepalives, so dead clients are cleaned up
  within ~45 seconds.
- A `SIGUSR1` handler registered via `faulthandler.register` dumps every
  Python thread's stack synchronously — this works even when the asyncio
  event loop is blocked, unlike `loop.add_signal_handler` which needs a
  live loop to deliver the callback. `SIGUSR2` logs a summary of active
  sessions and pending tasks.
- A plain TCP health endpoint listens on port 8023 for Kubernetes liveness
  probes. It replies `OK\n` and closes.

## IAC Subnegotiation (GMCP / MSSP / MTTS / MSP)

MUD-client accessibility tooling — sound packs, virtual buffers, gags,
speedwalk maps — runs on *out-of-band events* delivered over the telnet
IAC subnegotiation channel. django-moo speaks IAC on top of SSH: 0xFF
prefix bytes pass through SSH channels transparently, and
[sshelnet](https://gitlab.com/bubblehouse/sshelnet) bridges plain-telnet
clients onto the SSH port. No second listener is needed.

The IAC plumbing is **gated on the client's `TERM` value**. Vanilla SSH
clients (`TERM=xterm-256color`, `tmux`, `screen`, etc.) leave the channel
in default strict UTF-8 and never see an IAC byte — emitting one would
render as garbage in xterm. MUD clients opt in via either
`TERM=xterm-256-basic` (the existing raw-mode opt-in, also the default
sshelnet picks for telnet bridging) or a known MUD-client name
(`mudlet`, `tintin`, `mushclient`, ...). For those sessions,
`connection_made` switches the channel's UTF-8 error policy to
`surrogateescape` so 0xFF IAC bytes round-trip cleanly: outbound IAC
frames go out by decoding raw bytes through `surrogateescape` (the
channel's UTF-8 encoder re-emits them as the original bytes), and
inbound 0xFF arrives as `\udcff` surrogate chars in `data_received`,
which we re-encode for the IAC parser. The channel stays in str mode
the whole time, so prompt_toolkit's renderer, CPR detection, and
`Stdout` pipeline work unchanged.

`IacNegotiator` (also in `moo/shell/iac.py`) owns the per-session
capability state. On connect, the server offers `WILL GMCP`, `WILL MSSP`,
`WILL MSP`, `WILL EOR`, `WILL CHARSET`, `DO TTYPE`, `DO NAWS`; the
negotiator responds to counter-offers, runs the three-stage MTTS dance,
and accepts client-initiated CHARSET requests. Negotiated capabilities
are mirrored into `_session_settings[user_pk]["iac"]` and the Django
cache so Celery workers (verb execution) can branch on them.

Outbound GMCP emits go through the SDK: `send_gmcp(obj, module, data)`
in `moo/sdk/output.py` encodes the frame, publishes an
`{"event": "oob", "data": <bytes>}` Kombu message to the player's queue,
and the shell's `_route_event` writes the bytes straight to the channel
via `_chan_write_iac` (no LF→CRLF, no encoding). `play_sound` prefers
GMCP `Client.Media.Play` when negotiated and falls back to inline MSP
`!!SOUND(...)` markers otherwise. All SDK OOB entry points are
wizard-only, consistent with `write()` and `open_editor`.

After each prompt render, `_emit_prompt_end_marker` emits `IAC EOR`
(preferred) or `IAC GA` so screen readers can detect the
server-to-client turnaround and focus the input line. No-op for clients
that negotiated neither — the bytes would render as garbage in a plain
terminal.

Scope note: this is the IAC subnegotiation layer only. We do not
implement the wider telnet protocol (ECHO, SGA, LINEMODE, etc.) because
we do not need to — SSH already handles the transport.

## History

`RedisHistory` (`moo/shell/history.py`) is a small prompt_toolkit `History`
backed by the Django cache. Entries are stored as a list under
`moo:history:<user_pk>`, capped at 500 entries, and the TTL is refreshed on
every write so abandoned accounts eventually expire. It is wrapped in
`ThreadedHistory` in `process_commands_rich` so cache I/O does not block
the event loop.

## Further Reading

- {doc}`../how-to/connection-control` — player-facing toggles: `PREFIX`,
  `.flush`, etc.
- {doc}`../how-to/accessibility` — the `a11y` verb, OSC 133 markers, raw
  mode, and the upcoming OOB telnet protocol work.
- {doc}`../reference/runtime` — the `context` proxy that verb code uses to
  reach the shell's output handler.
- {doc}`../reference/tasks` — how Celery tasks publish output into the
  Kombu queue this document consumes.
