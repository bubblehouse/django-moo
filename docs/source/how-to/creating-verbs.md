# Creating MOO Verbs

This guide is the reference for writing verb code: the file format, the
names injected into the verb's scope, the parser API, the output
mechanisms, error handling, and the patterns most verbs share. For the
beginner walk-through, see {doc}`../tutorials/first-verb`. For patterns
beyond the basics — calling other verbs, time-aware continuation,
placement, SDK helpers — see {doc}`advanced-verbs`.

## The shebang line

Every verb file starts with a `#!moo verb` shebang that supplies the
verb's name(s), the object it lives on, and how the parser should match
it:

```python
#!moo verb take --on $thing --dspec this --ispec from:any
```

Grammar:

```text
#!moo verb verb_name1 [verb_name2] ...
    --on object_name
    [--dspec this|any|none|either]
    [--ispec PREP:SPEC [PREP:SPEC ...]]
```

- **Verb names** — space-separated. Multiple names act as aliases;
  inside the verb body, `verb_name` is the specific alias the player
  invoked.
- **`--on`** — required. Accepts a player name (`Wizard`), an object ID
  (`#5`), or a system property reference (`$thing`, `$room`,
  `$container`).
- **`--dspec`** — direct object specifier:
  - `this` — verb fires only when the parsed direct object resolves to
    the object the verb is on. (`drop widget` matches widget's `drop`.)
  - `any` — a direct object must be present; any string is accepted.
  - `either` — direct object is optional. `this` is set correctly when
    one is given.
  - `none` (the default) — verb only matches commands with no direct
    object.
- **`--ispec`** — indirect object specifiers, one per preposition.
  `--ispec on:this --ispec in:this` would let `put X on Y` and
  `put X in Y` reach the same verb. Use `none` when the preposition
  itself must be present but takes no object (e.g. `crawl --dspec none
  --ispec under:any` matches `crawl under desk`).

Examples from the default verbs:

```python
#!moo verb accept --on $room
#!moo verb take --on $thing --dspec this --ispec from:any
#!moo verb put give --on $thing --dspec this --ispec on:this --ispec in:this
#!moo verb @reload reload_batch --on $programmer --dspec any --ispec on:any
```

### Common `--ispec` choices

| Interaction | `--ispec` | Sample command |
|-------------|-----------|----------------|
| Talking to someone | `to:any` | `talk to barkeep` |
| Sitting / lying down | `on:this` | `sit on couch` |
| Putting items inside | `in:any` | `put bottle in bag` |
| Taking / drinking from | `from:this` | `drink from tap` |
| Examining via | `through:any` | `look through scope` |
| Attacking / aiming | `at:this` | `punch at dummy` |

## Words the parser treats as prepositions

The lexer scans every command for preposition words *before* it splits
the command into parts. Words like `from`, `to`, `with`, `in`, `on`,
`at`, and `into` are always preposition boundaries — even when they
appear inside what you intended to be a plain argument.

If a player is going to type something whose argument contains one of
those words, they need to quote it:

```text
@eval from moo.sdk import lookup       ← parsed as prep boundary; verb won't match
@eval "from moo.sdk import lookup"     ← preserved as a single argument
```

`@eval` pre-imports `moo.sdk`, so the example above is also avoidable
by writing `@eval "lookup('Wizard').location.name"`. The interactive
shell expands a leading `;` to `@eval`:

```text
; lookup('Wizard').location.name
```

The full preposition list lives in `settings.PREPOSITIONS` and is
documented in {doc}`../reference/parser`. When a verb takes free-form
text (a code snippet, a description, a message), document the quoting
expectation in the verb's help.

## RestrictedPython execution

Verb code is compiled and run inside Zope's RestrictedPython sandbox.
Practical implications:

- Only the modules in `settings.ALLOWED_MODULES` may be imported:
  `moo.sdk`, `hashlib`, `re`, `datetime`, `time`. Wizards additionally
  get `moo.core.models.{object,verb,property}`.
- Only the builtins in `settings.ALLOWED_BUILTINS` are available:
  `all`, `any`, `dict`, `enumerate`, `getattr`, `hasattr`, `list`,
  `max`, `min`, `set`, `sorted`, `sum`, and `PermissionError`. Other
  builtins (`type`, `dir`, `eval`, `exec`, `open`, ...) are absent by
  design.
- Attribute names beginning with `_` raise `AttributeError`. The single
  exception is the global `_` reference to the System Object.
- `str.format` and `str.format_map` are blocked on string instances —
  use f-strings or `str.replace()` instead.
- `return` may appear at any level of the verb body, not just at
  function end (RestrictedPython rewrites the source).

For the full sandbox model and the security rationale, see
{doc}`../reference/sandbox`.

## Names injected into the verb's scope

Every verb is compiled into a function with the signature
`def verb(this, passthrough, _, *args, **kwargs)`. Inside the body, the
following names are available without import:

| Name | Type | Description |
|------|------|-------------|
| `this` | `Object` | The object the verb was matched on. With `--dspec this`, that's the direct object. With `--dspec any` or `none`, it's the caller. **Use `context.player` for "who is acting" logic** — `this` is not always the caller (see {doc}`../reference/parser`). |
| `passthrough` | callable | Calls the same verb on the parent class. Pass any arguments through: `passthrough(*args, **kwargs)`. |
| `_` | `Object` | The System Object (`pk=1`). Used for `_.string_utils`, `_.gripe_recipients`, etc. |
| `args` | `list` | Positional arguments when the verb is invoked as a method. Empty when invoked from the command parser. |
| `kwargs` | `dict` | Keyword arguments when invoked as a method. Empty from the parser. |
| `verb_name` | `str` | The exact alias the caller used. **Do not assign to a local variable named `verb_name`** — Python scoping makes that a local for the entire function and reads before the assignment raise `UnboundLocalError`. Use a different name. |

Linters will complain about undefined references for `this`,
`passthrough`, `_`, `args`, `kwargs`, and `verb_name`. Add
`# pylint: disable=undefined-variable` at the top of every verb file.

## The `context` object

`from moo.sdk import context` brings the per-task context proxy into
scope. Most non-trivial verbs need it.

| Attribute | Description |
|-----------|-------------|
| `context.player` | The Object that originated the command. Stays anchored to the session initiator across nested verb calls. |
| `context.caller` | The object whose verb code is currently executing. Shifts as verbs invoke other verbs. |
| `context.parser` | The `Parser` for the current command. Provides `get_dobj()`, `get_dobj_str()`, etc. (See below.) |
| `context.writer` | The callable that prints to the player's connection. `print()` ends up calling this. |
| `context.task_id` | The Celery task ID for the current execution. |
| `context.task_time` | A `TaskTime` namedtuple (`elapsed`, `time_limit`, `remaining`). Used for handing off long-running work — see {doc}`advanced-verbs`. |
| `context.caller_stack` | Stack of caller frames as verbs invoke sub-verbs. Useful for permission auditing. |

`context.player` and `context.caller` are the same object at the start
of a command. They diverge once a verb on one object invokes a verb on
another — the new verb's `context.caller` is the new executor while
`context.player` stays the original session.

## Parser methods

When a verb is dispatched from a command, `context.parser` exposes the
parsed pieces:

| Method | Returns | Notes |
|--------|---------|-------|
| `get_dobj()` | Direct object as **Object** | Raises `NoSuchObjectError` if the dobj string isn't a real object in scope. |
| `get_dobj(lookup=True)` | Direct object as **Object**, by global name lookup | Use when the object isn't in the local area but needs to be addressed by name. |
| `get_dobj_str()` | Direct object as **string** | Safe for plain text arguments (names, messages). |
| `has_dobj()` / `has_dobj_str()` | bool | Whether the dobj resolved / whether a dobj string was given. |
| `get_pobj(prep)` | Indirect object as **Object** | Raises `NoSuchObjectError`, `NoSuchPrepositionError`. |
| `get_pobj(prep, lookup=True)` | Indirect object as **Object**, by global name | Same as `get_dobj(lookup=True)`. |
| `get_pobj_str(prep)` | Indirect object as **string** | Raises `NoSuchPrepositionError` if the preposition isn't in the command. |
| `has_pobj(prep)` / `has_pobj_str(prep)` | bool | |

Use `get_dobj_str()` / `get_pobj_str()` when the argument is plain text
(a message, a name to create). Use `get_dobj()` / `get_pobj()` when you
expect the argument to refer to an existing game object — and let the
exception propagate if it doesn't.

## Sending output to players

Three mechanisms exist:

| Mechanism | Recipient | Notes |
|-----------|-----------|-------|
| `print(msg)` | The player who ran the command | Buffered until the verb finishes. The standard way for command verbs to show results. |
| `obj.tell(msg)` | Any player Object | Goes through `$player.tell`, applying gag-list filtering and paranoia tracking. Immediate. |
| `write(obj, msg)` | Any player Object | Low-level connection write, bypasses all filtering. Wizard-owned verbs only. |

`print()` is what most command verbs use. `obj.tell()` is for sending
to players other than the initiator (or when player preferences should
be respected). `write()` is rare — only for system notifications that
must skip filtering.

**`return "string"` does not display anything in a command verb.** The
return value goes back to whatever invoked the verb — discarded for
top-level player commands. Always `print()` for player-visible output;
use a bare `return` to exit early:

```python
if not context.parser.has_dobj_str():
    print(f"Usage: {verb_name} <target>")
    return

print("Done.")
```

For tests where there is no live SSH connection, `tell()` and `write()`
emit `RuntimeWarning(f"ConnectionError({obj}): {msg}")`. Capture with
`pytest.warns(RuntimeWarning)` (see {doc}`../tutorials/testing-verbs`).

## Reading and writing properties

The Django ORM is available, but the helper methods on `Object` are
shorter and walk the inheritance chain:

```python
description = obj.get_property("description")
print(description)

obj.set_property("description", "A dark room.")
```

`__getattr__` on `Object` lets you write `obj.description` directly,
but it tries verb dispatch first and only falls through to property
lookup on miss — so it's two queries. Use `get_property()` when you
know it's a property.

**Don't pair `has_property` with `get_property`.** That's two database
queries for the same data. Catch the absence with `try/except`:

```python
from moo.sdk import NoSuchPropertyError

try:
    description = obj.get_property("description")
except NoSuchPropertyError:
    description = "You see nothing special."
```

Multi-line description text is automatically reflowed by the `description`
verb in `root_class/description.py` via `_.string_utils.rewrap()`:
single newlines collapse to spaces, double newlines become paragraph
breaks, and each paragraph wraps to 80 columns. To get the same
behaviour for a custom help verb or note's `read` verb, call `rewrap`
explicitly:

```python
text = obj.get_property("body")
print(_.string_utils.rewrap(text))
```

`obj.save()` is only required after changing intrinsic fields like
`name`, `unique_name`, `obvious`, or `owner`. `set_property` saves the
property row directly.

## Error handling

Every exception in `moo.core.exceptions` inherits from `UserError`.
When a `UserError` propagates out of a verb, the task runner
(`moo.core.tasks.parse_command`) catches it and shows the message to
the player as a bold red line. No `try/except` boilerplate is needed
just to report errors.

The common exceptions, all importable from `moo.sdk`:

| Exception | Default message |
|-----------|----------------|
| `NoSuchObjectError(name)` | `"There is no '<name>' here."` |
| `NoSuchVerbError(name)` | `"I don't know how to do that."` |
| `NoSuchPropertyError(name)` | `"There is no '<name>' property defined."` |
| `AmbiguousObjectError(name, matches)` | `"When you say '<name>', do you mean ...?"` |
| `UsageError(message)` | The message string |

Letting `get_dobj()` raise `NoSuchObjectError` is the right pattern when
the argument must resolve to a real object — the player sees the
canned message automatically. Catch only when you want a different
message or an alternative path:

```python
from moo.sdk import NoSuchObjectError

try:
    target = context.parser.get_dobj()
except NoSuchObjectError:
    print("You'll need to be more specific.")
    return
```

`UsageError` is the conventional way to signal bad syntax:

```python
from moo.sdk import UsageError

if not context.parser.has_dobj_str():
    raise UsageError(f"Usage: {verb_name} <target>")
```

Any uncaught exception that isn't a `UserError` shows
`"An error occurred while executing the command."` to regular players
and a full traceback to wizards.

## Permission checks

For verbs that mutate state, check before touching the database:

```python
if not this.can_caller("write"):
    print("Permission denied.")
    return
```

`can_caller(perm)` consults the ACL on `this` against the current
`context.caller`. Common permission names: `read`, `write`, `execute`,
`move`, `transmute`, `derive`, `develop`, `entrust`, `grant`. See
{doc}`permissions` for the full set.

## Validating arguments

Validate early; report once with a single `print()` and an early
return:

```python
if not context.parser.has_dobj_str():
    print(f"Usage: {verb_name} <target>")
    return
```

Or raise `UsageError` and let the task runner format it:

```python
from moo.sdk import UsageError

if not context.parser.has_dobj_str():
    raise UsageError(f"Usage: {verb_name} <target>")
```

## A real verb, end to end

`default_verbs/thing/take.py` puts most of the patterns above into one
file:

```python
#!moo verb take --on $thing --dspec this --ispec from:any

# pylint: disable=return-outside-function,undefined-variable

from moo.sdk import context, NoSuchObjectError

# If "from <target>" was given, verify the object is actually placed on/near that target.
if context.parser.has_pobj_str("from"):
    try:
        from_target = context.parser.get_pobj("from")
        placement = this.placement
        if placement is None or placement[1] != from_target:
            tname = context.parser.get_pobj_str("from")
            print(f"{this.title()} isn't on the {tname}.")
            return
    except NoSuchObjectError:
        tname = context.parser.get_pobj_str("from")
        print(f"There is no '{tname}' here.")
        return

title = this.title()
if this.location == context.player:
    print(f"You already have {title} in your inventory.")
elif this.moveto(context.player):
    this.clear_placement()
    print(this.take_succeeded_msg(title))
    if msg := this.otake_succeeded_msg(title):
        this.location.announce(msg)
else:
    print(this.take_failed_msg(title))
    if msg := this.otake_failed_msg(title):
        this.location.announce(msg)
```

What's going on:

- The shebang fires this verb when `take widget` matches a `$thing` and
  optionally accepts a `from <target>` clause.
- `context.parser.has_pobj_str("from")` and `get_pobj("from")` extract
  the optional `from` argument, treating "object not found" as a
  user-facing error.
- `this.title()` is a helper verb on `$thing` that returns the
  formatted name.
- `this.moveto(context.player)` calls another verb on the object —
  see {doc}`advanced-verbs` for how that works.
- `this.take_succeeded_msg(title)` returns a pronoun-substituted
  string. Helper verbs like this *do* return values (because they're
  invoked as methods, not as parser commands). The pattern is covered
  in {doc}`advanced-verbs`.
- `this.location.announce(msg)` broadcasts to everyone else in the
  room.

## Where to go next

- {doc}`advanced-verbs` — calling other verbs, `passthrough()`,
  helper verbs that return values, time-aware continuation,
  placement, SDK helpers.
- {doc}`../reference/parser` — full parser reference, preposition
  synonyms, verb search order.
- {doc}`../reference/sandbox` — what RestrictedPython blocks and why.
- {doc}`../reference/runtime` — full `context` reference.
- {doc}`../reference/builtins` — every callable exposed by `moo.sdk`.
