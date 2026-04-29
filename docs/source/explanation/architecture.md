# Architecture

DjangoMOO's overarching goals are similar to LambdaMOO's — a
persistent, multi-user, programmable text world — but the
implementation is independent and the architectural choices are
modern:

- **100% Python.** Both the runtime and the in-game programming
  language are Python; no MOO bytecode interpreter, no DSL.
- **Django-backed.** The ORM, admin, auth, and migration tooling do
  what would otherwise be hand-rolled.
- **Celery-backed.** Verb execution, scheduled tasks, and command
  parsing all run as Celery tasks, with standard back-pressure and
  retry semantics. Many deployment targets are supported.
- **Sandboxed.** Verb code runs inside Zope's RestrictedPython,
  inside a Celery worker process, inside a Django atomic
  transaction, with a hard time limit on every invocation.

The result is a system that's highly available (any component can
be replicated), horizontally and vertically scalable, and easy to
develop on (standard Django/Celery conventions throughout). Docker
Compose handles local dev; the same images run in Kubernetes via
the Helm chart in `extras/helm/`.

## Antioch — django-moo's predecessor

A lot of the architecture decisions and proofs of concept for
django-moo come from lessons learned building
[antioch](https://github.com/philchristensen/antioch), which started
in 1999–2000 — long before Django, modern web frameworks, or robust
async tooling existed. Antioch's hand-rolled equivalents of those
layers became more painful to maintain over time, and led to a few
operating principles for django-moo:

- For a niche project, lean on third-party libraries wherever they
  reduce surface area.
- Don't try to compete with modern graphical games; the constraints
  of text are a storytelling feature, not a limitation.
- Plan for testability from day one.

## Components

```
        ┌───────────────────────────────────────────────────────────┐
        │  Web (uWSGI)                                              │
        │  - Django admin (wizard ops)                              │
        │  - WebSSH (browser terminal)                              │
        │  - django-allauth registration flow                       │
        └─────────────────────────┬─────────────────────────────────┘
                                  │
        ┌─────────────────────────┴─────────────────────────────────┐
        │  PostgreSQL                                               │
        │  - canonical state (Object, Verb, Property, ACL, Player)  │
        │  - migrations, admin tables                               │
        └─────────────────────────┬─────────────────────────────────┘
                                  │
        ┌─────────────────────────┴─────────────────────────────────┐
        │  Redis                                                    │
        │  - Tier-2 cross-session cache (verb/property lookups)     │
        │  - Django session storage                                 │
        │  - Celery broker (task queue)                             │
        │  - Kombu exchanges (async tells, OOB events)              │
        └─────────────────────────┬─────────────────────────────────┘
                                  │
        ┌─────────────────────────┴─────────────────────────────────┐
        │  Celery workers                                           │
        │  - parse_command / parse_code / invoke_verb               │
        │  - RestrictedPython sandbox + atomic txn + time limit     │
        └─────────────────────────┬─────────────────────────────────┘
                                  │
        ┌─────────────────────────┴─────────────────────────────────┐
        │  AsyncSSH server (port 8022)                              │
        │  - prompt-toolkit TUI (rich mode)                         │
        │  - line-based output (raw mode for MUD clients)           │
        │  - IAC subnegotiation (GMCP/MTTS/MSSP/EOR/CHARSET/MSP)    │
        └───────────────────────────────────────────────────────────┘
```

## Front-end

The primary interface is SSH — connect with any client to port 8022,
authenticate by password or registered SSH key (see
{doc}`../how-to/ssh-key-management`), and you get a prompt-toolkit
TUI driven by `moo/shell/prompt.py`. For users who can't or don't
want to install an SSH client, WebSSH at port 443 provides a
browser terminal that bridges to the same SSH listener.

The web port also serves the Django admin (for wizard-level
operations) and a registration flow built on
[django-allauth](https://allauth.org/). The signup form collects
standard credentials plus the MOO-specific fields (character name,
gender, optional description) and creates a `Player` row linking
the Django user to a freshly-created avatar Object. Templates live
under `moo/shell/templates/`.

For full client/protocol details (rich vs. raw mode, OSC 133, the
two coroutines, the Kombu bus), see {doc}`shell-internals`.

## Back-end

A Django management command launches the SSH server (`moo_shell`),
which uses AsyncSSH to accept connections and dispatch each session
to a `MooPromptToolkitSSHSession`. The session embeds a
`prompt-toolkit` `Application` for the rich TUI; the in-app Python
REPL for wizards is `ptpython`-flavoured.

The web app is served by uWSGI (`extras/uwsgi/uwsgi.ini`), which
also serves Django static files and routes registration / admin
requests.

## Workers and execution

Every command and verb invocation is a Celery task. This gives:

- **Process isolation** — a memory race or runaway loop in a worker
  cannot affect other concurrent invocations. Workers can be
  bounded by the OS.
- **Atomic transactions** — every task body runs inside
  `transaction.atomic()`. Uncaught exceptions roll back the entire
  task's database changes.
- **Hard time limit** — read from the `CELERY_TASK_TIME_LIMIT`
  environment variable in `moo/celeryconfig.py` (default `3`
  seconds). When the limit elapses, Celery terminates the worker.
  Synchronous calls to other verbs share the budget; the time-aware
  continuation pattern in {doc}`../how-to/advanced-verbs` hands work
  off to a fresh task before the limit hits.
- **Sandbox** — Zope's RestrictedPython compiles verb source under
  guards for attribute access, item access, builtins, and imports.
  See {doc}`sandbox` for the model and {doc}`../reference/sandbox`
  for the full enforcement detail.

In development, a Celery Beat scheduler runs in-process to drive
periodic tasks. Production typically separates beat into its own
deployment.

## Storage

Game state lives in three tiers:

- **PostgreSQL** is the source of truth — Objects, Verbs,
  Properties, ACLs, Players, Mail rows, ancestry cache.
- **Redis** holds session storage, the Celery task queue, the
  per-session Kombu queues for async tells and OOB events, and the
  Tier-2 attribute cache for verb/property lookups (verb dispatch
  hits PostgreSQL only on a cache miss).
- An in-process **session cache** inside each `ContextManager` scope
  is the Tier-1 hot path; repeat reads of the same property within
  one command are free.

The full architecture, including the `AncestorCache` denormalised
table that replaces recursive CTEs, is documented in
{doc}`../reference/caching`.

## Out-of-band protocols

For MUD-client compatibility, django-moo speaks GMCP, MTTS/TTYPE,
MSSP, GA/EOR, CHARSET, and MSP over the SSH transport. IAC byte
sequences pass through SSH transparently; the IAC parser/encoder/
negotiator lives in `moo/shell/iac.py`. The
[sshelnet](https://gitlab.com/bubblehouse/sshelnet) bridge translates
plain telnet to SSH for clients that lack native SSH support, so no
second listener is needed.

The full protocol stack and which capabilities verb code can emit
(via `moo.sdk.send_gmcp`, `moo.sdk.play_sound`, etc.) are documented
in {doc}`../how-to/accessibility`.

## Where things live

| Module | Responsibility |
|--------|----------------|
| `moo.core.models` | Django models (Object, Verb, Property, ACL, Player, Mail). |
| `moo.core.code` | RestrictedPython compilation, `ContextManager`, sandbox guards. |
| `moo.core.parse` | Lexer + Parser; verb dispatch. |
| `moo.core.tasks` | Celery task definitions (`parse_command`, `parse_code`, `invoke_verb`). |
| `moo.shell` | AsyncSSH server, prompt-toolkit shell, Kombu consumer, IAC layer. |
| `moo.bootstrap` | Dataset initialisation; `default/` package and verb files. |
| `moo.sdk` | Public verb-author API — exclusive import target for verb code. |
| `moo.settings` | Django settings split (`base.py`, `dev.py`, `local.py`, `test.py`). |
| `extras/helm` | Kubernetes deployment chart. |
| `extras/mudlet` | Mudlet client package (mapper bridge, SSH launcher). |

## See also

- {doc}`shell-internals` — the SSH session lifecycle, the two
  coroutines, OSC 133, IAC negotiation in detail.
- {doc}`parser` — the command-parser model.
- {doc}`sandbox` — why the sandbox exists and how it's structured.
- {doc}`introduction` — Diátaxis-style intro to the docs as a whole.
