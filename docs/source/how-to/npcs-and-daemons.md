# NPCs and Daemons

Two classes from the `default` bootstrap let you add autonomous
behaviour to a world:

- `$daemon` — an invisible scheduler that fires a verb on a
  configurable interval. Use it for ambient effects, periodic
  housekeeping, broadcasts, or anything that should happen "in the
  background" with no player attention.
- `$npc` — an actor the parser sees as a player. Inherits from both
  `$player` (so `look`, `tell`, gender, and parser identity work) and
  `$daemon` (so it ticks on a schedule). `$wanderer` is a small
  subclass that demonstrates the pattern.

Both ship with two wizard convenience commands — `@daemon` and `@npc`
— that cover the common lifecycle operations.

## When to reach for which

Use a `$daemon` when nothing needs to be visible in the room and the
behaviour is "tick a verb every N seconds." Examples: announce a chime
on the hour, sweep stale guest accounts, restock a vendor's inventory.

Use a `$npc` (or a subclass of it) when you want something players can
look at, talk to, or address as a target — and that also acts on its
own. The class costs you a `Player` row and parser dispatch overhead,
so don't reach for it when a daemon would do.

## Daemon lifecycle

Every `$daemon` carries five properties that change over its life:

| Property | Purpose |
|----------|---------|
| `interval` | seconds between ticks; default `60` |
| `target` | the Object the daemon acts on or speaks to (your subclass uses this however it wants) |
| `periodic_task_id` | PK of the live `django_celery_beat.PeriodicTask`, or `None` if disabled |
| `tick_count` | total ticks since last reset |
| `last_tick_at` | ISO-8601 timestamp of the most recent tick |

### Create

`@daemon` is wizard-only. A daemon is just an Object whose class chain
includes `$daemon`:

```text
@create $daemon called "Town Crier"
@daemon list
```

For richer behaviour, define your own subclass with verbs:

```text
@create $daemon called "Generic Town Crier"
@eval _.town_crier = lookup("Generic Town Crier")
```

Then attach an `on_tick` verb to your subclass — the dispatcher fires
that verb on each tick:

```python
#!moo verb on_tick --on $town_crier

# pylint: disable=return-outside-function,undefined-variable

target = this.get_property("target")
if target is not None:
    target.tell(f"The town crier rings the hour: {this.tick_count} bells.")
```

### Enable, disable, trigger

```text
@daemon enable Town Crier
@daemon trigger Town Crier   # fires once now, synchronously, for testing
@daemon disable Town Crier
@daemon list                 # show all daemons with status
```

`enable` creates a `django_celery_beat.PeriodicTask` through
{func}`~moo.sdk.invoke` ``(periodic=True)`` and records the PK on the
daemon. `disable` calls {func}`~moo.sdk.cancel_scheduled_task` and
clears the pointer. Both are idempotent.

`trigger` skips the schedule and calls `this.tick()` directly, which
does the bookkeeping (`tick_count` += 1, `last_tick_at` = now) and
then your `on_tick`. Use it while developing the verb.

### Recycle

`@daemon kill Town Crier` calls `disable()` and then `delete()`. The
inherited `$daemon.recycle` verb also fires `disable()`, so direct
`obj.delete()` won't leak a `PeriodicTask`.

## NPC lifecycle

`$npc` is a `$player` and a `$daemon`. Its `on_tick` calls
`this.act()` — the personality hook. Subclasses override `act` to
decide what to do each cycle. The base `act` is a no-op.

### Create

```text
@npc create Cat
```

This calls `create(name, parents=[$npc], location=context.player.location)`
and immediately calls {func}`~moo.sdk.ensure_player_record` so the
parser sees `is_player() == True`. The NPC is *not* connected, so any
`tell()` to it silently drops.

To base an NPC on a custom subclass, use `from`:

```text
@npc create Crow from $wanderer
```

For full programmatic control from a bootstrap or verb:

```python
from moo.sdk import create, ensure_player_record, lookup

cat = create("Cat", parents=[lookup("$npc")], location=lookup("The Garden"))
ensure_player_record(cat)
```

`$npc.initialize` also calls `ensure_player_record` as a safety net —
direct `create()` calls don't need to do it themselves, but the
explicit call in `@npc create` is intentional because some downstream
code reads `is_player()` synchronously and the initialize verb fires
on a separate task.

### Schedule

Once created, an NPC is just a daemon — start it like any other:

```text
@daemon enable Cat
@daemon trigger Cat       # fire act() once now
@daemon disable Cat
@daemon kill Cat          # disable, drop Player row, delete Object
```

`$npc.recycle` calls {func}`~moo.sdk.remove_player_record` and then
`disable()`. The explicit `disable()` call is needed because
`passthrough()` from `$npc.recycle` reaches `$root_class.recycle`
through the `$player` branch and never visits `$daemon`.

### Authoring an `act` verb

`act` runs in the daemon's task context. The NPC is `this`. The
`context.parser` is `None` (no player command triggered this).
`context.player` is the NPC itself.

```python
#!moo verb act --on $cat

# pylint: disable=return-outside-function,undefined-variable

import random

if not this.location:
    return

choices = ["The cat stretches.", "The cat washes one paw.", "The cat yawns."]
this.location.announce_all_but(this, random.choice(choices))
```

`announce_all_but(this, msg)` is the canonical broadcast call for
"everyone in this room except me." It uses `tell()` so gag-list
filtering and paranoia tracking apply.

## Wanderer: a worked example

`$wanderer` is shipped as a complete NPC subclass. It carries three
extra properties:

| Property | Default | Purpose |
|----------|---------|---------|
| `wander_rooms` | `[]` | List of room PKs the wanderer may visit |
| `wander_leave_msg` | `"%N wanders off."` | Broadcast in the room being left |
| `wander_arrive_msg` | `"%N wanders in."` | Broadcast in the room being entered |

The `act` override picks a random room from `wander_rooms` (excluding
the current location), runs both messages through `pronoun_sub` with
`%N` set to the wanderer's name, and teleports through `moveto`.

Set destinations through the `@npc destinations` wizard subcommand:

```text
@npc create Crow from $wanderer
@npc destinations Crow #20 #21 #22 #23
@daemon enable Crow
```

`@npc destinations Crow` with no PK list prints the current
destinations.

## When the parser dispatches verbs on a daemon or NPC

Daemon ticks never run through the parser. `context.parser` is `None`
inside `on_tick`, `tick`, or `act`. If your verb wants to fall back to
parser-style argument lookup, you must guard:

```python
if context.parser and context.parser.has_dobj_str():
    target_name = context.parser.get_dobj_str()
else:
    target_name = args[0] if args else None
```

`$npc` *is* parser-visible — players can `look` at it, `give` it
things, or `whisper` to it. Verb dispatch follows the usual
caller → inventory → location → dobj → pobj order. If you want the
NPC to respond to direct address (`hello Cat`), add the verb to the
NPC's class with `--dspec this`.

## Where to look for more

- `moo/bootstrap/default/verbs/daemon/` — base class implementation
- `moo/bootstrap/default/verbs/npc/` — `$npc`-specific extensions
  (including the `moveto` override that resolves the multi-parent
  ambiguity)
- `moo/bootstrap/default/verbs/wanderer/act.py` — the canonical
  worked subclass
- `moo/bootstrap/default/tests/test_daemon.py` and `test_npc.py` —
  test patterns for time-based verbs
- {doc}`../reference/objects` — the class hierarchy table
- {doc}`../reference/builtins` — {func}`~moo.sdk.invoke`,
  {func}`~moo.sdk.cancel_scheduled_task`,
  {func}`~moo.sdk.get_scheduled_task_info`,
  {func}`~moo.sdk.ensure_player_record`,
  {func}`~moo.sdk.remove_player_record`
