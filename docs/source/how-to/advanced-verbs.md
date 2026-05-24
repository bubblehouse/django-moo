# Advanced Verb Patterns

Patterns that build on the basics in {doc}`creating-verbs`: calling
other verbs, parent dispatch with `passthrough()`, helper verbs that
return values, async and time-budget handling, spatial placement, and
the rest of the `moo.sdk` toolkit.

## Calling other verbs

The Django ORM doesn't honour MOO inheritance, so `Object` provides
helper methods that walk the parent chain:

```python
obj.invoke_verb("announce", "broadcast text")

# Or via __getattr__:
obj.announce("broadcast text")
```

`__getattr__` first looks for a verb by that name, then falls through
to property lookup. Each call counts against the calling task's 3-second
time limit.

A real verb that demonstrates the pattern is
`default/verbs/thing/take.py`:

```python
elif this.moveto(context.player):
    this.clear_placement()
    print(this.take_succeeded_msg(title))
    if msg := this.otake_succeeded_msg(title):
        this.location.announce(msg)
```

Three verbs are invoked here without explicit imports:

- `this.moveto(context.player)` runs the `moveto` verb on `this` (or
  an inherited one from a parent class). It returns a truthy value on
  success.
- `this.take_succeeded_msg(title)` is a helper verb that *returns* a
  formatted string — see "Helper verbs that return values" below.
- `this.location.announce(msg)` runs the `announce` verb on the room.

## `passthrough()` for parent dispatch

`passthrough` is the MOO equivalent of `super()`. It calls the same
verb on the next ancestor up the parent chain, so a child can run
type-specific logic and then defer to the generic behaviour.

`default/verbs/thing/moveto.py` is the reference:

```python
#!moo verb moveto --on $thing

# pylint: disable=return-outside-function,undefined-variable

where = args[0]

# Clear placement for any objects placed on this one in the current room.
# Runs before the move so this.location is still the source room.
if this.location:
    for placed in list(this.placed_objects.filter(location=this.location).all()):
        placed.clear_placement()

if where.is_unlocked_for(this):
    return passthrough(where)
return False
```

The thing-specific work — clearing placements of objects sitting on this
one — runs first, then `passthrough(where)` defers to
`$root_class.moveto`, which performs the actual database move. If the
lock check fails, the verb returns `False` without calling the parent.

Pass through any `args`/`kwargs` you received; the parent verb's
signature has no idea which child invoked it:

```python
return passthrough(*args, **kwargs)
```

## Helper verbs that return values

The "return values are discarded" warning in {doc}`creating-verbs`
applies only to verbs invoked from the command parser. Verbs invoked
*as methods* — `obj.foo()` — return values normally. Most non-trivial
default verbs use a layer of helpers that return strings to be
`print()`ed by the parser-facing verb.

`default/verbs/thing/messages.py` defines eight such helpers in one
file:

```python
#!moo verb otake_succeeded_msg otake_failed_msg take_succeeded_msg take_failed_msg odrop_succeeded_msg odrop_failed_msg drop_succeeded_msg drop_failed_msg --on $thing

# pylint: disable=return-outside-function,undefined-variable

prop_value = this.get_property(verb_name)

title = this.title()
prop_value = prop_value.replace("%T", title.capitalize()).replace("%t", title)

return _.string_utils.pronoun_sub(prop_value)
```

The shebang lists eight aliases, and the body uses `verb_name` to read
the matching property. `take.py` then calls
`this.take_succeeded_msg(title)`, gets a string back, and `print()`s
it. The format-code substitution and pronoun rewrite are concentrated
in one place rather than duplicated across `take.py`, `drop.py`, and
their failure paths.

This is the right shape for any "build a string that another verb will
display" helper.

## Asynchronous and delayed execution with `invoke()`

`moo.sdk.invoke()` enqueues a verb for later execution as its own
Celery task. Each invocation gets a fresh 3-second budget.

```{eval-rst}
.. py:currentmodule:: moo.sdk
.. autofunction:: invoke
   :no-index:
```

Use cases:

- **Delayed execution** — schedule a verb to run after a delay
  (`delay=N` seconds).
- **Periodic execution** — `periodic=True` keeps re-firing on the same
  interval. Wizard-only.
- **Cron schedules** — `cron="<expression>"` for time-of-day style
  triggers. Wizard-only.
- **Time-aware continuation** — hand off remaining work to a fresh
  task before the current task's budget runs out (see below).

```python
from moo.sdk import invoke, context

# Run the same verb again 30 seconds from now.
invoke(context.parser.verb, delay=30)
```

For periodic tasks that should also re-use existing verb code, pass a
callback verb:

```python
from moo.sdk import invoke, context

if context.parser is not None:
    say = context.caller.get_verb("say", recurse=True)
    invoke(verb=context.parser.verb, callback=say, delay=30, value=0)
    return
value = kwargs["value"] + 1
return f"A parrot squawks {value}."  # passed to the callback verb
```

## Time-aware continuation

Each verb invocation, including synchronous calls to other verbs, must
finish within the configured task time limit (3 seconds by default).
For loops over many objects, check the remaining budget and hand the
unfinished work to a fresh task before being killed.

`task_time_low()` returns `True` when the current task is near its
limit; `schedule_continuation()` re-invokes the verb with the remaining
work as `args[0]`.

```python
from moo.sdk import context, task_time_low, schedule_continuation
```

Inside the loop, dispatch on `verb_name` so a single file handles both
the parser entry point and the continuation re-entry:

```python
if task_time_low():
    schedule_continuation(items[i:], this.get_verb("my_batch"))
    return
```

`default/verbs/programmer/at_reload.py` is the canonical
implementation. The relevant excerpt:

```python
#!moo verb @reload reload_batch --on $programmer --dspec any --ispec on:any

def do_reload_batch(verbs):
    count = 0
    for i, verb in enumerate(verbs):
        if task_time_low():
            schedule_continuation(
                verbs[i:],
                this.get_verb("reload_batch"),
                msg=f"  Time limit approaching; continuing in a new task ({len(verbs) - i} verb(s) remaining)...",
            )
            return True, count
        context.player.tell(f"  Reloading {verb}...")
        verb.reload()
        count += 1
    return False, count


if verb_name == "reload_batch":
    # Continuation entry: args[0] is a list of Verb PKs from the prior task.
    verbs = list(Verb.objects.filter(pk__in=args[0]))
    continued, count = do_reload_batch(verbs)
    if not continued:
        context.player.tell(f"Reloaded {count} verb(s).")
else:
    # Parser entry: gather the work, kick off the loop.
    ...
```

Things to keep in mind:

- Use `context.player.tell()` (not `print()`) for progress messages.
  `tell()` delivers immediately; `print()` buffers until the verb
  returns, so the player wouldn't see anything until the very end.
- Materialise the queryset with `list()` before the loop so the
  database cursor isn't held open across the time check.
- Define a separate alias (`reload_batch`) for the continuation entry
  point. Dispatch on `verb_name`, not on `args[0]`'s type.
- Keep continuation args minimal — the list of remaining work is
  enough; progress was already delivered via `tell()`.
- Never assign to a local named `verb_name`. Python scoping makes the
  whole function treat it as a local, and reads before the assignment
  raise `UnboundLocalError`. See the gotcha in {doc}`creating-verbs`.

## Returning a value from a verb

`return` may appear at any depth in verb code (not just at function
end), thanks to RestrictedPython's compilation. Use it for two things:

1. **Helper verbs** that build strings or compute state for another
   verb to consume (see "Helper verbs that return values" above).
2. **Early exits** in command verbs — bare `return`, no value. The
   string version is silently discarded:

```python
if not args:
    print(f"Usage: {verb_name} <object_name>")
    return                                        # exits cleanly

if not args:
    return f"Usage: {verb_name} <object_name>"   # WRONG — player sees nothing
```

## Placement verbs

Objects can be placed in a spatial relationship to another object in
the same room. Two fields on the Object record the placement:

- `placement_prep` — preposition string (`"on"`, `"under"`, `"behind"`,
  `"before"`, `"beside"`, `"over"`).
- `placement_target` — the Object it is placed relative to.

`PLACEMENT_PREPS` (from `moo.sdk`) lists every valid preposition.
`HIDDEN_PLACEMENT_PREPS` is the subset (`"under"`, `"behind"`) whose
placed items don't appear in the room's contents listing and aren't
findable by name through the parser.

Placement is cleared automatically when an object is taken, dropped,
or moved. If the placement target is deleted, both fields go to
`None`.

### Writing a placement verb

```python
#!moo verb place --on $thing --dspec this --ispec on:any --ispec under:any --ispec behind:any --ispec before:any --ispec beside:any --ispec over:any

from moo.sdk import context, NoSuchPropertyError, UsageError, PLACEMENT_PREPS

prep = None
for p in PLACEMENT_PREPS:
    if context.parser.has_pobj_str(p):
        prep = p
        break

if prep is None:
    raise UsageError(f"Usage: place <object> {'/'.join(PLACEMENT_PREPS)} <target>")

target = context.parser.get_pobj(prep)

# Optional: check surface_types restriction on the target
try:
    allowed = target.get_property("surface_types")
    if prep not in allowed:
        print(f"You can't place things {prep} the {target.title()}.")
        return
except NoSuchPropertyError:
    pass

this.set_placement(prep, target)
print(f"You place {this.title()} {prep} the {target.title()}.")
context.player.location.announce(
    f"{context.player.title()} places {this.title()} {prep} the {target.title()}."
)
```

Key points:

- `--ispec` must enumerate every supported preposition; there is no
  wildcard form.
- `set_placement(prep, target)` is atomic: it sets both fields and
  saves in one call.
- `clear_placement()` removes placement without touching other fields.

### Reading placement

```python
placement = this.placement      # (prep, target) or None
if placement is None:
    print(f"The {this.title()} is not placed anywhere.")
else:
    prep, target = placement
    print(f"The {this.title()} is {prep} the {target.title()}.")
```

### Restricting surface types

Set the `surface_types` property on a target to limit which prepositions
it accepts:

```python
desk.set_property("surface_types", ["on", "beside"])
# Now: "place book on desk" succeeds; "place book under desk" fails.
```

If `surface_types` is absent, all placement prepositions are accepted.

## Common SDK helpers

`moo.sdk` exposes more than the basics covered in
{doc}`creating-verbs`. The functions you'll reach for most often
beyond `lookup`/`create`/`write`:

- **Tasks**: `invoke`, `cancel_scheduled_task`,
  `get_scheduled_task_info`, `task_time_low`, `schedule_continuation`,
  `set_task_perms`, `invoked_verb_name`.
- **Full-screen UIs**: `open_editor`, `open_paginator`,
  `can_open_editor`.
- **Players**: `players`, `connected_players`, `owned_objects`,
  `owned_objects_by_pks`, `ensure_player_record`,
  `remove_player_record`.
- **Client capabilities**: `get_client_mode`, `get_wrap_column`,
  `get_session_setting`, `set_session_setting`.
- **Out-of-band protocols**: `send_gmcp`, `play_sound`,
  `room_info_payload` — see {doc}`accessibility` for the protocol
  story.
- **Admin**: `boot_player`, `server_info`.
- **Mail**: `send_message`, `get_mailbox`, `count_unread`, etc.

For the full inventory with signatures and arguments, see
{doc}`../reference/builtins`.

### Editor callback example

`default/verbs/note/edit.py` opens an editor pre-filled with the
note's body, and routes the saved text back into a callback verb:

```python
from moo.sdk import context, open_editor

existing = this.get_property("body", default="")
open_editor(context.player, existing, this.set_body)
```

`this.set_body` is another verb on the note that takes the saved text
as its first argument and writes it to the `body` property. The editor
runs in the SSH process; the callback fires as a fresh Celery task
once the player saves.

### Mode-aware verbs

When a verb would open a TUI, branch on `get_client_mode()` so MUD
clients and screen-reader users still get usable output:

```python
from moo.sdk import get_client_mode, open_editor

if get_client_mode() == "raw":
    print(f"Use: @edit description with \"your text here\"")
    return
open_editor(context.player, existing_text, this.set_description)
```

See {doc}`accessibility` for the full mode-selection model.

## Verb time limits

Each verb invocation, including synchronous calls to other verbs,
finishes within `CELERY_TASK_TIME_LIMIT` (default 3 seconds) or the
worker kills it. For longer work:

- Compose into multiple verb invocations via `invoke()` — each gets
  its own 3-second budget.
- Use the time-aware continuation pattern above for loops over many
  items.
- For wall-clock waits ("happen 30 seconds from now"), use
  `invoke(verb, delay=30)` rather than blocking inside a verb.

## Where to go next

- {doc}`creating-verbs` — basics: shebang, parser, output, errors,
  properties.
- {doc}`../reference/builtins` — full SDK function reference.
- {doc}`../reference/runtime` — `context` attributes, `task_time`.
- {doc}`../reference/parser` — verb search order, preposition synonyms.
- {doc}`../reference/sandbox` — RestrictedPython model and the
  underscore/format/QuerySet guards.
