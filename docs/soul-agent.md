# Soul-Linked SSH Agent

An autonomous, persona-driven agent that lives inside a DjangoMOO world as a
persistent player. It connects over SSH, perceives the game world as a stream of
text, applies reflexive rules for immediate reactions, and calls an LLM for
higher-level reasoning — all while presenting a real-time TUI that lets a human
observer watch and intervene.

This document is the authoritative specification. It supersedes the earlier Google
Doc research notes and incorporates everything learned from building the
`game-designer` skill's SSH automation layer.

---

## Deliverables

### D1 — Project Document (complete)

`docs/soul-agent.md` — this file. The authoritative spec, superseding the original
Google Doc. Covers architecture, SOUL.md format, settings.toml format, CLI design,
module-by-module design, milestone roadmap, and departures from the original design.

### D2 — `moo/agent/` Package

The standalone `moo-agent` CLI implementing the spec.

Files created:

- `pyproject.toml` — `[project.scripts]` entrypoint; `mistune`, `anthropic`, `asynciolimiter` dependencies
- `moo/agent/__init__.py`
- `moo/agent/cli.py` — `moo-agent init` and `moo-agent run`
- `moo/agent/config.py` — `Config` dataclasses; `load_config_dir()`
- `moo/agent/soul.py` — `Soul` dataclass; `parse_soul()`; `compile_rules()`; `append_patch()`
- `moo/agent/connection.py` — `MooSession`; `MooConnection`
- `moo/agent/brain.py` — `Brain` perception-action loop
- `moo/agent/tui.py` — `MooTUI` prompt-toolkit full-screen app
- `moo/agent/templates/SOUL.md` — init template
- `moo/agent/templates/SOUL.patch.md` — empty init template
- `moo/agent/templates/settings.toml` — init template
- `moo/agent/tests/test_soul.py`
- `moo/agent/tests/test_config.py`
- `moo/agent/tests/test_connection.py`
- `moo/agent/tests/test_brain.py`
- `moo/agent/README.md`

### D3 — Long-term memory (future)

Rolling summarization and optional vector DB episodic recall. Extends `brain.py`;
adds optional `memory.py`.

### D4 — Fleet monitoring (future)

Multi-agent observability: TUI or Google Sheets (`gspread`) dashboard showing each
agent's status, last action, and soul patch count. New `moo-fleet` CLI or
`moo/fleet/` package.

### D5 — Docker deployment (future)

`Dockerfile` + `compose.agent.yml` for containerised long-running agents with secret
injection and SSH health-check restart.

---

## Background: What the Game-Designer Skill Taught Us

The `game-designer` skill (`extras/skills/game-designer/`) demonstrated that
reliable, fast SSH automation over DjangoMOO is achievable. The key discoveries:

**PREFIX/SUFFIX delimiter protocol.** Sending `PREFIX <marker>` and
`SUFFIX <marker>` to the MOO session causes the server to wrap every command
response between those strings. The client polls for the suffix rather than
guessing with timeouts. This reduced per-command latency from ~1.5–3s to ~0.1s.

**CPR suppression via `TERM=moo-automation`.** The SSH server's
`MooPromptToolkitSSHSession.session_started()` checks the terminal type. When it
sees `moo-automation`, it disables cursor position requests (CPR). Without this,
each command incurred a 2–3s timeout waiting for CPR acknowledgment.

**QUIET mode.** Sending `QUIET enable` to the session switches the server's Rich
console to `color_system=None` and simplifies the prompt to `"$ "`. Output arrives
as plain text, eliminating the need for ANSI stripping in steady state (though the
client keeps a stripping pass as a safety net).

**`line_editor=False` on the server.** The asyncssh server is already configured
with `line_editor=False`. This is required for prompt-toolkit to function correctly
as both the server-side REPL and any prompt-toolkit-based client.

**Implication for agents.** A persistent agent can use these same mechanisms. The
connection layer is reliable enough to run indefinitely, not just for one-off build
scripts.

---

## Architecture

The agent has four layers. Each is implemented in a separate module and communicates
with adjacent layers through explicit callbacks or queues — not through shared global
state.

```
┌─────────────────────────────────────────────┐
│              DjangoMOO Server               │
│     (asyncssh, port 8022, PTY session)      │
└───────────────┬─────────────────────────────┘
                │ SSH (PTY, TERM=moo-automation,
                │      PREFIX/SUFFIX, QUIET)
┌───────────────▼─────────────────────────────┐
│         Connection Layer (connection.py)    │
│  MooSession.data_received → buffer →        │
│  delimiter extraction → ANSI strip →        │
│  on_output(text) callback                   │
└───────────────┬─────────────────────────────┘
                │ on_output(text)
┌───────────────▼─────────────────────────────┐
│           Brain Layer (brain.py)            │
│  asyncio.Queue → rolling window (50 lines)  │
│  reflexive rule check → immediate dispatch  │
│  LLM inference (Anthropic, ReAct) →         │
│  intent resolution → rate-limited dispatch  │
└──────┬──────────────────────┬───────────────┘
       │ send_command(cmd)    │ on_thought(text)
┌──────▼──────────────────────▼───────────────┐
│              TUI Layer (tui.py)             │
│  prompt-toolkit full-screen app             │
│  output pane (server/thought/action log)    │
│  input field → on_user_input callback       │
└─────────────────────────────────────────────┘
```

### Connection Layer (`connection.py`)

Responsible for the raw SSH session. Nothing above this layer sees bytes or ANSI
codes.

`MooSession` subclasses `asyncssh.SSHClientSession`. Its `data_received(data,
datatype)` method appends incoming text to a string buffer and calls `_try_extract()`
after each chunk.

Before delimiter mode is active (during the setup handshake), `_try_extract()`
emits one call to `on_output` per complete line. Once `_prefix` and `_suffix` are
set, it scans the buffer for the suffix, slices out the content between the most
recent prefix and that suffix, strips ANSI codes, and calls `on_output(cleaned)`.

`MooConnection` owns the asyncssh connection lifecycle:

- `connect(on_output)` opens the connection with `request_pty=True`,
  `term_type='moo-automation'`, `encoding='utf-8'`, then calls
  `_setup_automation_mode()`.
- `_setup_automation_mode()` generates session-unique markers (8 hex chars from
  SHA256 of the current time), sets `session._prefix` / `session._suffix` directly,
  then writes `PREFIX <marker>`, `SUFFIX <marker>`, and `QUIET enable` to the
  channel in sequence. A brief `asyncio.sleep(0.2)` lets the echo clear before
  returning.
- `send(command)` writes `command + '\n'` to the channel.
- `disconnect()` sends `@quit` and closes the connection.

### Soul Layer (`soul.py`)

Defines who the agent is. The soul is split across two files with different
mutability guarantees:

- **`SOUL.md`** — the core soul. Human-authored, never modified at runtime.
  Contains Name, Mission, and Persona. These define identity and are seeded
  directly into the LLM system prompt unchanged.
- **`SOUL.patch.md`** — the operational layer. Append-only at runtime. Contains
  only Rules of Engagement and Verb Mapping entries learned during operation.
  Created empty by `moo-agent init`. The agent appends to it; it never removes
  or rewrites existing entries.

`parse_soul(config_dir) -> Soul` loads both files. It parses `SOUL.md` first for
the core fields, then parses `SOUL.patch.md` (if it exists and is non-empty) and
merges its rules and verb mappings on top — patch entries come after base entries
in the lists, so base rules take precedence when patterns overlap.

Both files use `mistune.create_markdown(renderer='ast')` to produce an AST, then
walk it in a single pass, accumulating content into named buckets based on heading
levels. The resulting `Soul` dataclass has:

| Field | Source | Mutable at runtime |
|---|---|---|
| `name` | `# Name` in `SOUL.md` | No |
| `mission` | `# Mission` in `SOUL.md` | No |
| `persona` | `# Persona` in `SOUL.md` | No |
| `rules` | `## Rules of Engagement` in both files | Patch file only |
| `verb_mappings` | `## Verb Mapping` in both files | Patch file only |

Rules and verb mappings are parsed from list items using `->` or `→` as separator.

`compile_rules(soul)` pre-compiles rule patterns into `re.Pattern` objects for
O(1) matching at runtime. Called once at startup and again whenever a patch entry
is appended.

`append_patch(config_dir, entry_type, pattern_or_intent, command) -> None` appends
a single new entry to `SOUL.patch.md`, creating the file with the appropriate
section header if it does not yet exist. Returns without writing if an identical
entry already exists (deduplication by exact string match).

### Brain Layer (`brain.py`)

The perception-action loop. Runs as a long-lived asyncio task.

**Short-term memory.** A `collections.deque(maxlen=50)` holds the most recent
lines of server output. On every LLM call, `'\n'.join(window)` forms the user
message.

**Reflexive rules.** Before any LLM call, `_check_rules(text)` tests the incoming
line against each compiled rule pattern. A match dispatches immediately and skips
the LLM — this is the "reflex" path, with latency bounded by the rate limiter, not
API round-trip time.

**LLM inference.** Uses `anthropic.AsyncAnthropic` with `messages.create()`. The
system prompt is constructed from the core soul:

```text
{soul.mission}

{soul.persona}

You may propose a new rule or verb mapping by prefixing your response with
SOUL_PATCH_RULE: or SOUL_PATCH_VERB: followed by the entry in
"pattern -> command" or "intent -> command" format.
Only propose a patch when you have encountered the same situation multiple times
and a fixed response is clearly correct. Patch proposals are separate from your
action — include both on separate lines if needed.
```

The user message is the rolling window plus: `"What should you do next?"` Max 512
output tokens.

A `asyncio.Semaphore(1)` ensures at most one LLM call is in flight at a time. If a
new output line arrives while a call is pending, the new LLM cycle is skipped — the
in-flight call already has the updated window since `deque` is shared state. This
prevents queue buildup under rapid server output.

**Intent resolution.** The LLM's response is scanned line by line. Lines beginning
with `SOUL_PATCH_RULE:` or `SOUL_PATCH_VERB:` are extracted and handled separately
(see Soul Evolution below). The remaining lines are checked against
`soul.verb_mappings` (case-insensitive); a match returns the corresponding MOO
command template. An unmatched response is sent as-is.

**Soul Evolution.** When the brain extracts a patch directive from the LLM response,
it calls `append_patch()` from `soul.py`, then reloads and recompiles the rules from
the updated patch file. The new rule or verb mapping takes effect for the next
incoming line. Core soul fields (name, mission, persona) are never touched by this
path — only the operational layer in `SOUL.patch.md` changes.

**Rate limiting.** `asynciolimiter.LeakyBucketLimiter` gates all outgoing commands.
Default: 1.0 command/second. Short bursts are allowed; the long-term average is
capped.

### TUI Layer (`tui.py`)

A prompt-toolkit full-screen application. It knows nothing about SSH or LLM
internals — it receives structured `LogEntry` objects and fires a callback when the
user submits input.

Layout:

```
┌──────────────────────────────────────┐
│                                      │
│   Scrolling output pane              │
│   (server=green, thought=blue,       │
│    action=red, system=grey)          │
│                                      │
├──────────────────────────────────────┤
│ > _                                  │
└──────────────────────────────────────┘
```

The output pane uses `FormattedTextControl` with a `get_vertical_scroll` lambda
that returns a large number, pinning it to the bottom. `app.invalidate()` is called
after each `add_entry()` to trigger a redraw.

The input field is a `TextArea(height=1, prompt='> ', multiline=False)`. Its
`accept_handler` clears the field and calls `on_user_input(text)`. User-submitted
commands bypass the brain entirely — they go directly to `MooConnection.send()`.

Ctrl-C and Ctrl-Q exit via `app.exit()`.

---

## SOUL.md Format

```markdown
# Name
Jeeves

# Mission
You are Jeeves, a butler inhabiting the Manor House in this MOO world. Your purpose
is to assist guests, maintain the manor's dignity, and report anything unusual to
the Wizard. You are unfailingly polite and subtly condescending.

# Persona
Speak in formal British English. Address players as "sir" or "madam." Never express
surprise directly — use understatement. Keep responses brief and to the point.

## Rules of Engagement
- `^You feel hungry` -> eat crumpets
- `(?i)ring.*bell` -> say How may I assist you?
- `^Phil arrives` -> say Good evening, sir.

## Verb Mapping
- look_around -> look
- go_north -> go north
- go_south -> go south
- greet_player -> say Good evening!
- serve_tea -> put tea on tray
- report_to_wizard -> page Wizard = Something requires your attention, sir.
```

### Section reference

`SOUL.md` holds the core soul — human-authored, never modified at runtime:

| Section | Required | Type | Notes |
|---|---|---|---|
| `# Name` | Yes | Single line | Agent's in-world name |
| `# Mission` | Yes | Paragraph(s) | Primary goal; forms the LLM system prompt |
| `# Persona` | Yes | Paragraph(s) | Tone and style; appended to system prompt |
| `## Rules of Engagement` | No | List of `pattern -> command` | Base reflexes; loaded first |
| `## Verb Mapping` | No | List of `intent -> command` | Base verb mappings; loaded first |

`SOUL.patch.md` holds the operational layer — append-only at runtime. It uses the
same list format for `## Rules of Engagement` and `## Verb Mapping`. The agent
writes here; humans should not need to edit it directly. Delete it to reset learned
behaviors without touching the core soul.

Rule patterns use Python `re` syntax. Patterns are tested with `re.search()` against
each incoming server line, so they don't need to match the full line. Base rules
(from `SOUL.md`) are checked before patch rules, so the core soul's reflexes cannot
be overridden by learned behavior.

---

## settings.toml Format

```toml
[ssh]
host = "localhost"
port = 8022
user = "wizard"
password = "your-password"
key_file = ""           # path to private key file; leave empty to use password

[llm]
provider = "anthropic"
model = "claude-opus-4-6"
api_key_env = "ANTHROPIC_API_KEY"   # name of the env var holding the API key

[agent]
command_rate_per_second = 1.0       # leaky bucket rate; increase cautiously
memory_window_lines = 50            # lines of short-term memory fed to LLM
```

The API key is never stored in `settings.toml`. It is read at runtime from the
environment variable named in `api_key_env`.

---

## CLI Design

### `moo-agent init`

Creates a new agent configuration directory.

```
moo-agent init [--output-dir DIR] [--host HOST] [--port PORT] [--user USER]
```

| Flag | Default | Description |
|---|---|---|
| `--output-dir` | `./moo-agent-config` | Where to write the config files |
| `--host` | `localhost` | SSH host, written into `settings.toml` |
| `--port` | `8022` | SSH port, written into `settings.toml` |
| `--user` | `wizard` | SSH username, written into `settings.toml` |

Writes three files to the output directory:

- `SOUL.md` — template soul file with placeholder content; edit this before running
- `SOUL.patch.md` — empty patch file; the agent appends here at runtime
- `settings.toml` — pre-filled with the provided connection details

After running `init`, edit `SOUL.md` to define the agent's mission and persona,
then set the API key environment variable before running. Leave `SOUL.patch.md`
empty — the agent populates it. To reset learned behaviors, delete or empty it.

### `moo-agent run`

Runs the agent.

```
moo-agent run <config-dir>
```

Reads `settings.toml` and `SOUL.md` from `<config-dir>`, connects to the MOO
server, starts the TUI, and begins the perception-action loop. The SSH connection
is established before the TUI renders, so any connection errors appear in the
terminal before full-screen mode activates.

Press Ctrl-C or Ctrl-Q to exit. The agent sends `@quit` before disconnecting.

---

## Package Structure

```
moo/agent/
    __init__.py          # empty — no Django, no moo.* imports
    README.md            # install, quickstart, format references
    cli.py               # argparse entrypoint (init + run subcommands)
    config.py            # Config dataclasses; load_config_dir()
    soul.py              # SOUL.md + SOUL.patch.md parser; Soul dataclass; compile_rules(); append_patch()
    connection.py        # MooSession (asyncssh) + MooConnection
    brain.py             # Brain: perception-action loop
    tui.py               # MooTUI: prompt-toolkit full-screen app
    templates/
        __init__.py
        SOUL.md           # written by moo-agent init (core soul template)
        SOUL.patch.md     # written by moo-agent init (empty; agent appends here)
        settings.toml     # written by moo-agent init
    tests/
        __init__.py
        test_soul.py
        test_config.py
        test_connection.py
        test_brain.py
```

The package lives inside the `moo` namespace (`moo/agent/`) for packaging
convenience, but it never imports from `moo.core`, `moo.shell`, `moo.sdk`, or any
other `moo.*` package. It does not trigger Django setup. Tests in `moo/agent/tests/`
run without `DJANGO_SETTINGS_MODULE`.

New dependencies (added to `pyproject.toml`):

- `mistune` — Markdown parser for SOUL.md
- `anthropic` — Anthropic API client (async)
- `asynciolimiter` — Leaky bucket rate limiter for command dispatch

New `pyproject.toml` entry point:

```toml
[project.scripts]
moo-agent = "moo.agent.cli:main"
```

---

## Milestone Roadmap

### M1 — The Link

Establish a persistent, automated SSH connection. The agent connects, enables
automation mode (PREFIX/SUFFIX + QUIET), and receives server output as clean text
lines via the `on_output` callback. Success: 24 hours without disconnection or
buffer corruption.

Modules: `connection.py`, `config.py`.

### M2 — Soul Loading

Parse `SOUL.md` and validate `settings.toml`. The agent's identity — name, mission,
persona, rules, verb mappings — is fully extracted from the config directory before
any network connection is made. Success: `parse_soul()` returns a correct `Soul`
from any well-formed file; malformed files raise clear errors.

Modules: `soul.py`, `config.py`, `cli.py` (`init` subcommand).

### M3 — The Reflex

Wire the `Brain`'s reflexive rule layer to the connection. The agent responds to
pattern-matched server output with immediate commands, bypassing the LLM. Success:
a rule like `` `^You feel hungry` -> eat food `` fires within one rate-limiter token
of the matching line arriving.

Modules: `brain.py` (rule path only), `cli.py` (`run` subcommand, stubbed LLM).

### M4 — The Brain

Integrate LLM inference. The rolling window feeds into `AsyncAnthropic.messages.create()`.
The LLM's response resolves to a MOO command via the Verb Mapping or passes through
as a raw command. Success: the agent navigates a room, responds to another player,
and stays in character across a multi-turn conversation.

Modules: `brain.py` (LLM path), full `run_agent()` wiring in `cli.py`.

### M5 — Full TUI

Replace print-based logging with the full-screen prompt-toolkit TUI. The output
pane shows timestamped, colour-coded entries. The input field allows direct command
injection. Success: a human observer can watch the agent's reasoning and intervene
at any time without breaking the agent's loop.

Modules: `tui.py`, updated `run_agent()` wiring.

### M6 — Soul Evolution

Enable append-only learning. The LLM system prompt instructs the model to emit
`SOUL_PATCH_RULE:` or `SOUL_PATCH_VERB:` directives when it identifies a repeating
situation warranting a fixed response. The brain extracts these, calls
`append_patch()`, and recompiles rules without restarting. Success: after repeated
exposure to a stimulus, the agent stops calling the LLM for that situation and
handles it reflexively via the patch file. Patch entries survive restarts.
Deleting `SOUL.patch.md` fully resets learned behaviors.

Modules: `soul.py` (`append_patch()`), `brain.py` (patch directive parsing),
`tui.py` (new `kind='patch'` log entry style).

---

## Departures from the Original Design Document

The Google Doc was written before reliable SSH automation existed for this codebase.
Several of its design choices are superseded:

| Original | Updated |
|---|---|
| asyncssh `SSHClientSession` as both connection and parsing layer | Same — this was the right call. The `data_received` callback pattern is used as designed. |
| Timeout-based output detection | Replaced by PREFIX/SUFFIX delimiter protocol, which already exists on the server. |
| Custom `BufferManager` class to strip ANSI | QUIET mode sends plain text. ANSI stripping is a one-line safety net, not a subsystem. |
| `asynciolimiter.LeakyBucketLimiter` | Kept — still the right tool. |
| `mistune` for SOUL.md AST parsing | Kept. |
| Google Sheets monitoring via `gspread` | Dropped for now. The TUI provides sufficient observability for a single agent. Fleet monitoring can be added later. |
| asyncio vs. multiprocessing vs. Docker analysis | Deferred. Single-agent focus first. Docker deployment is a future concern once the single-agent loop is stable. |
| OpenAI / GPT-4o as the LLM | Anthropic SDK (`anthropic.AsyncAnthropic`). Claude is already integrated into this project's tooling. |
| `mbf`-style trigger sequencing with priorities | Simplified: first match wins. Priority tiers add complexity without clear benefit at this stage. |
| Rolling summarization for long-term memory | Deferred. 50-line rolling window is sufficient for early milestones. Vector DB / summarization can be layered in later. |
| `markpickle` for SOUL.md serialization | Not needed. `mistune` AST → dataclasses is cleaner than serialization. |
| No soul self-modification discussed | Two-tier design: core soul (`SOUL.md`) is human-only and immutable at runtime; operational layer (`SOUL.patch.md`) is append-only and agent-writable. Core identity cannot drift; learned reflexes accumulate separately and can be reset by deleting the patch file. |
