# Accessibility and MUD Client Compatibility

DjangoMOO aims to work for two audiences that most modern codebases forget:

- **Screen-reader users who connect via SSH.** A full-screen prompt_toolkit
  TUI with ANSI colour and cursor manipulation is hostile to a screen reader
  unless the server emits structural hints the reader can follow.
- **Players using traditional MUD clients.** Mudlet, TinTin++, MUSHclient and
  friends expect a plain line-oriented text stream, often with
  out-of-band telnet subnegotiation for structured events. The prompt_toolkit
  TUI confuses all of them.

This guide covers what the server offers today and what is coming. For the
player-facing verbs that sit on top — `PREFIX`, `OUTPUTPREFIX`, `.flush` —
see {doc}`connection-control`. For the internal mechanics (OSC 133 emission,
the Kombu bus, the two coroutines), see
{doc}`../explanation/shell-internals`.

## The `a11y` Verb

All three user-tunable accessibility settings live on a single verb
(`@accessibility` is the long alias). Each setting is an `on`/`off` toggle,
session-scoped, and cleared on disconnect.

```
a11y                    Show all current settings
a11y <setting> on       Turn a setting on
a11y <setting> off      Turn a setting off
```

| Setting    | Default | Effect                                                                |
|------------|---------|-----------------------------------------------------------------------|
| `osc133`   | on      | Emit OSC 133 semantic shell markers around prompts, commands, output. |
| `prefixes` | off     | Prepend `[ERROR]`/`[WARN]`/`[INFO]` textual tags to coloured output.  |
| `quiet`    | off     | Suppress Rich colour codes; simplify the prompt to a bare `$`.        |

Example session:

```
a11y prefixes on
a11y osc133 off
a11y quiet on
```

### `on`/`off` versus prepositions

`on` and `off` are MOO prepositions, and a verb that expects them as
prepositional objects would see them stripped by the parser. `a11y` reads
directly from `context.parser.words` — the raw tokenised command —
specifically to sidestep that quirk. If you write your own toggle verbs,
either do the same, or use words that are not in `settings.PREPOSITIONS`.

## OSC 133 — Semantic Shell Integration

Modern terminals (iTerm2, Ghostty, WezTerm, Kitty, Windows Terminal) and
screen readers (VoiceOver's terminal integration, NVDA with custom MUD
scripts, Emacspeak) support OSC 133 markers that bracket each interactive
cycle:

| Marker               | Meaning                              |
|----------------------|--------------------------------------|
| `ESC]133;A`          | prompt start                         |
| `ESC]133;B`          | command start (end of prompt)        |
| `ESC]133;C`          | output start                         |
| `ESC]133;D;<status>` | command end with exit status         |

With OSC 133 on (the default), users can navigate command-by-command
instead of line-by-line, copy a whole command block in one keystroke, and
hear "command succeeded" / "command failed" announced by status. Disabling
it is useful when copying transcripts out of a terminal that renders the
raw escapes as glyphs.

See {doc}`../explanation/shell-internals` § "OSC 133 Semantic Shell
Integration" for how the markers survive prompt redraws without looking
like a fresh command boundary on every async tell.

## Text Prefixes for Screen Readers

`a11y prefixes on` makes the server wrap coloured severity output in
textual tags:

```
[ERROR] You can't take that.
[WARN]  That exit is locked.
[INFO]  You enter the parlour.
```

The tags survive `a11y quiet on` (which strips ANSI), survive copy/paste to
a clipboard that does not preserve colour, and are announced by a screen
reader as distinct words. With prefixes off, severity is carried by colour
alone.

Both the default verb library and any custom verbs you write participate
automatically — the wrapping happens at the shell's Rich-rendering layer,
not at the call site. See the `_prefixes_enabled()` check in
`moo/shell/prompt.py` for the plumbing.

## `quiet` Mode

`a11y quiet on` turns off Rich colour rendering entirely and reduces the
prompt to a bare `$`. The terminal still receives ANSI cursor motion from
prompt_toolkit itself — quiet is about colour, not about becoming a
different kind of terminal.

Quiet mode matters for:

- Scripts that parse command output (ANSI escapes confuse string matching).
- Screen readers that speak escape codes as garbage characters.
- Transcripts piped to files that will later be grepped or diffed.

The older `QUIET enable` / `QUIET disable` command has been replaced by
`a11y quiet on` / `a11y quiet off`. If you were using it, update your
scripts.

## The `WRAP` Verb

The server's render layer wraps long lines at the terminal width it last
detected. Screen readers and narrow-window users may want a different
wrap. The `WRAP` verb controls it:

```
WRAP          Show current setting and effective width
WRAP auto     Use the actual terminal width (default)
WRAP 120      Set to a fixed number of columns
```

`WRAP` persists across sessions — it is stored as the `wrap_column`
property on the player object, not as a session setting.

## Raw Mode for MUD Clients

Clients that cannot handle cursor manipulation or bracketed paste — Mudlet,
TinTin++, MUSHclient, BlowTorch, classic telnet wrappers — request raw
mode by setting `TERM=xterm-256-basic` before connecting:

```bash
TERM=xterm-256-basic ssh wizard@moo.example.com
```

In raw mode:

- No prompt_toolkit `Application` is instantiated.
- The prompt is written line-by-line; async output just lands on new lines.
- Editor TUIs (`@edit`) are rejected with a hint pointing at the inline
  `@edit ... with "..."` form, so the client can still set content without
  a full-screen editor.
- Paginator output is inlined rather than shown in a pager.
- OSC 133 markers are still emitted if `a11y osc133 on` (the default), so
  terminal-aware MUD clients that understand them still work.

The `moo.sdk.get_client_mode()` function returns `"raw"` or `"rich"`. Verbs
that would normally open an editor or paginator check this and route to
inline alternatives instead.

See {doc}`../explanation/shell-internals` § "The Three Modes" for the full
mode-selection logic.

## Upcoming: Out-of-Band Telnet Protocols (Issue #16)

Raw mode gets a MUD client connected, but it stops at "plain line stream".
Blind MUD players have spent decades building client-side tooling — sound
packs, virtual output buffers, gag filters, speedwalk maps, vitals readouts
— that works dramatically better when the server emits structured *out-of-band*
events alongside the human-readable text.

GitLab issue
[#16](https://gitlab.com/bubblehouse/django-moo/-/issues/16) scopes the
support. django-moo is SSH-only, but
[sshelnet](https://gitlab.com/bubblehouse/sshelnet) bridges plain-telnet
clients onto the SSH port, and IAC byte sequences pass through SSH
transparently — so the full suite of telnet-subnegotiation MUD protocols
can be implemented without a second listener.

### Tier 1 — the OOB channel

| Protocol | Telnet option | What it does |
|----------|---------------|--------------|
| **IAC state machine**  | — | Inbound parser (`DO`/`DONT`/`WILL`/`WONT` + `SB…SE`), outbound encoder, per-session negotiation state. Lands as a new `moo/shell/telnet.py`. |
| **GMCP** (Generic MUD Communication Protocol) | 201 | JSON-over-subneg side channel. Emits `Core.Hello`, `Char.Name`, `Char.Vitals`, `Room.Info`, `Room.Players`, `Comm.Channel.Text`. The canonical modern OOB protocol. |
| **MTTS / TTYPE** | 24 | Three-stage terminal-type negotiation. Replaces the fragile `TERM=xterm-256-basic` opt-in — Mudlet and friends will auto-select raw mode without environment magic. |

### Tier 2 — protocol polish

| Protocol | Telnet option | What it does |
|----------|---------------|--------------|
| **MSSP** | 70 | MUD-server status, answers discovery probes from The Mud Server Status Protocol directory and the Mudlet directory. |
| **GA / EOR** | 249 / 25 | Prompt-end signal. Critical for screen readers — tells the client "the server is done talking; focus the input line." |
| **CHARSET** | 42 | Lock the session to UTF-8 so clients that default to Latin-1 do not mojibake. |

### Tier 3 — audio UI

| Protocol | What it does |
|----------|--------------|
| **MSP** (MUD Sound Protocol) | Inline `!!SOUND(file.wav V=100)` / `!!MUSIC(...)` markers in the text stream. |
| **GMCP `Client.Media.Play`** | Same event, delivered via GMCP for clients (e.g. Mudlet) that prefer it. |

An `moo.sdk.output.play_sound(obj, name, volume=100, priority=10)` helper
will prefer GMCP when negotiated and fall back to MSP otherwise. **The
server ships protocol support only — no bundled sound assets.** Wizards and
pack authors wire events to files themselves.

### Rich-mode freebie: category metadata

The GMCP encoder needs to know that a given line of output is a
`Comm.Channel.Text` event rather than a `Room.Info` event, so an optional
`category=` kwarg will be added to `tell()` / `print()` — or a new
`emit(category, text, payload)` helper. Categories are metadata, **not** a
fourth output channel: `tell` vs `print` vs `write` stays as-is. As a side
benefit, rich-mode clients will be able to set per-category colours via a
new `COLORS` session setting (`COLORS chat=cyan room=dim.white combat=red`)
— default empty, no visible change for existing users.

### Deferred out of scope

Named side-windows (split panes), NAWS, MCCP2/3 compression, MXP, and MSDP
are all explicitly deferred — see issue #16 for the reasoning on each.

## Testing Your Setup

A few minimal checks you can run today:

```
a11y                    → prints three lines, current state of each
a11y prefixes on
look                    → expect [INFO] on any informational response
a11y quiet on
look                    → expect plain output, no ANSI escapes
```

For OSC 133, inspect the raw bytes:

```bash
ssh wizard@moo.example.com | cat -v | head
```

Expect `^[]133;A^G` before each prompt and `^[]133;D;0^G` after successful
commands. If they are missing, check `a11y` — `osc133` may have been turned
off by a previous session setting that leaked through.

For raw mode, set `TERM=xterm-256-basic` and verify that `@edit here` is
rejected with the inline-form hint rather than dropping you into a
full-screen editor.
