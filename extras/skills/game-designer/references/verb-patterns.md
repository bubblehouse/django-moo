# Verb Code Patterns

All verbs run inside the RestrictedPython sandbox.

**No shebang in SSH-edited verbs.** The `#!moo verb name --on $obj` shebang is only for bootstrap verb *files* in `moo/bootstrap/default_verbs/`. When you create a verb via `@edit verb <name> on "<obj>"` in an SSH session, the verb name and target are already registered by that command — the code body starts directly with imports.

## Imports

```python
from moo.sdk import context, create, lookup, invoke
from moo.sdk import NoSuchObjectError, NoSuchVerbError, NoSuchPropertyError
import random
import time
```

Available restricted imports: `moo.sdk`, `re`, `datetime`, `time`, `hashlib`, `random`

## Output

```python
# Send text to the calling player
print("You do the thing.")

# Announce to everyone in the room except the caller
context.player.location.announce_all_but(context.player, "Someone does the thing.")

# Announce to everyone in the room except the caller (shorter form, excludes context.player implicitly)
context.player.location.announce("Someone does the thing.")

# Announce to everyone including the caller
context.player.location.announce_all("A thing happens.")
```

Never use `return "message"` — returned values are not displayed. Use `print()` for player-visible output and bare `return` for early exit.

## Readable Objects — Use `$note`

For any object with readable text (sign, menu, letter, plaque, book, bulletin board), use `$note` as the parent. The player types `read <object>` to see the `text` property. No custom verb needed.

```
@create "chalkboard menu" from "$note"
@describe "chalkboard menu" as "Today's specials are scrawled on the chalkboard."
@edit property text on "chalkboard menu" with "Duff Draft - $2\nNachoBeer - $3\nFlaming Moe - $5"
@move "chalkboard menu" to "The Bar"
```

For a fixed sign (not portable), add a `moveto` verb returning `False`:

```
@create "warning sign" from "$note"
@edit verb moveto on "warning sign"
```

Verb body:

```python
return False
```

**Aliases for disambiguation.** If a room has more than one readable object, every `$note` object needs specific aliases so `read sign` resolves correctly. Include the generic word (`sign`, `menu`, `letter`) and at least one more specific alias:

```
@alias "chalkboard menu" as "menu"
@alias "chalkboard menu" as "chalkboard"
@alias "chalkboard menu" as "board"
```

**Signs and room descriptions:** Put the sign's text in the `text` property, not in the room description. The room description should acknowledge the sign's presence; the player reads it themselves:

```
# Room description:
A chalkboard hangs behind the bar with today's specials.

# NOT in the room description:
A chalkboard lists Duff Draft ($2), NachoBeer ($3), Flaming Moe ($5).
```

The exception: if the text is essential context (a room name carved in stone, a one-word warning), it can appear in the room description. Use judgment — if a player could plausibly skip reading it, use `$note`.

## Openable Containers — Use `$container`

For any object a player can open, close, and store things inside (chest, cabinet, safe, bag, drawer), use `$container` as the parent. It provides `open`/`close`/`put`/`take` verbs automatically, tracks the open/closed state, and — because it extends `$thing` — is portable by default.

```
@create "oak cabinet" from "$container"
@describe "oak cabinet" as "A tall oak cabinet with iron hinges."
@move "oak cabinet" to "The Study"
```

Players can then `open oak cabinet`, `put book in oak cabinet`, and `get book from oak cabinet`.

To make a container immovable (a built-in cabinet, a heavy safe), add a `moveto` verb that returns `False`:

```
@edit verb moveto on "oak cabinet"
```

Verb body:

```python
return False
```

Then set a `take_failed_msg` to explain why:

```
@edit property take_failed_msg on "oak cabinet" with "The cabinet is built into the wall."
```

To lock a container so it requires a key:

```
@lock_for_open "oak cabinet" with "brass key"
```

The player must hold an object named `brass key` to open it.

**`$container` vs `$thing`:** Use `$container` any time the object can hold things and be opened. Use `$thing` for sealed props that never open. Do not use `$furniture` for containers — it adds `sit`/`stand` instead of `open`/`close`.

## Sittable Objects — Use `$furniture`

For any object a player can sit on (chair, bench, couch, crate, boulder), use `$furniture` as the parent instead of `$thing`. It provides `sit`/`stand` verbs automatically, tracks seated state on the player, and prevents the object from being picked up:

```
@create "bar stool" from "$furniture"
@describe "bar stool" as "A cracked vinyl stool bolted to the floor."
@move "bar stool" to "The Bar"
```

Players can then `sit bar stool` and `stand`. Customize the experience with `_msg` properties:

```
@edit property sit_succeeded_msg on "bar stool" with "You perch on the cracked vinyl stool."
@edit property take_failed_msg on "bar stool" with "The stool is bolted to the floor."
```

See [object-model.md](object-model.md) for the full list of `$furniture` message properties.

## State Toggle (lock/unlock, fill/empty, on/off)

For binary state that doesn't involve sitting or opening containers, track state via a property and toggle it in a verb. (For openable containers use `$container` — it handles open/close natively.)

```python
from moo.sdk import context, NoSuchPropertyError

occupied = this.get_property("occupied")
if occupied:
    this.set_property("occupied", False)
    print("You open it.")
    context.player.location.announce_all_but(context.player, f"{context.player.name} opens it.")
else:
    this.set_property("occupied", True)
    print("You close it.")
    context.player.location.announce_all_but(context.player, f"{context.player.name} closes it.")
```

## One-Shot Event (banana peel, trap, explosive)

Fires once with full effect; subsequent triggers get an "already happened" message. Resets after one day so the event can fire again.

```python
from moo.sdk import context, NoSuchPropertyError
import datetime

try:
    last_fired = this.get_property("last_fired")
    elapsed = datetime.datetime.now() - datetime.datetime.fromisoformat(last_fired)
    cooled_down = elapsed.total_seconds() > 86400
except NoSuchPropertyError:
    cooled_down = True

if not cooled_down:
    print("Nothing more happens. The moment has passed.")
else:
    this.set_property("last_fired", datetime.datetime.now().isoformat())
    print("It happens. Dramatically.")
    context.player.location.announce_all_but(context.player, f"{context.player.name} triggers it.")
```

## Consume Item (drink, eat)

```python
from moo.sdk import context

full = this.get_property("full")
brand = this.get_property("brand")
if not full:
    print(f"The {brand} glass is empty.")
    return
this.set_property("full", False)
print(f"You drink the {brand}. Refreshing.")
context.player.location.announce_all_but(context.player, f"{context.player.name} drinks a {brand}.")
```

## Create Item on Demand (pull tap, order drink)

```python
from moo.sdk import context, create, lookup

beer_glass = lookup("Generic Beer Glass")
glass = create("a pint of Duff", parents=[beer_glass], location=context.player)
glass.set_property("full", True)
glass.set_property("brand", "Duff")
print("You pull a pint of Duff. Foam settles.")
context.player.location.announce_all_but(context.player, f"{context.player.name} pulls a pint.")
```

## NPC Dialogue (speak verb on NPC)

```python
from moo.sdk import context
import random

lines = this.get_property("lines")
msg = random.choice(lines)
print(f'{this.name} says, "{msg}"')
context.player.location.announce_all_but(context.player, f'{this.name} says, "{msg}"')
```

The `lines` property is a list of strings set via `@edit property lines on "NPC" with ["line1", "line2"]`.

## Random Outcome (dartboard, jukebox, slot machine)

```python
from moo.sdk import context
import random

outcomes = this.get_property("outcomes")
result = random.choice(outcomes)
print(f"You throw. {result}")
context.player.location.announce_all_but(context.player, f"{context.player.name} throws a dart. {result}")
```

## Prank Call Pattern (phone booth, payphone)

```python
from moo.sdk import context
import random

names = this.get_property("names")
name = random.choice(names)
print(f"You dial the number. Moe picks up.")
print(f'"Hey Moe, is {name} there?"')
print(f'Moe\'s voice: "Uh... {name}? Hey, is there a {name} in here?"')
context.player.location.announce_all_but(
    context.player,
    f"{context.player.name} is using the payphone."
)
```

## Property Access Patterns

```python
from moo.sdk import NoSuchPropertyError

# Read a property (raises NoSuchPropertyError if missing)
val = this.get_property("name")

# Read with fallback
try:
    val = this.get_property("name")
except NoSuchPropertyError:
    val = "default"

# Write a property
this.set_property("name", value)

# Access another object's property
room = context.player.location
owner = room.get_property("owner")
```

## Object Lookup

```python
from moo.sdk import lookup, NoSuchObjectError

# By name — raises NoSuchObjectError if not found (never returns None)
obj = lookup("The Bar")

# Check existence
try:
    obj = lookup("The Bar")
except NoSuchObjectError:
    print("Room not found.")
    return
```

## Invoke Another Verb

```python
from moo.sdk import invoke

# Call a verb by passing a Verb reference (obtained via attribute access)
invoke(verb=obj.verb_name, args=(arg1, arg2))

# With a delay (seconds)
invoke(verb=obj.verb_name, delay=10)
```

## Context Object

```python
context.player        # The player who ran the command
context.player.name   # Their name
context.player.location  # The room they're in
this                  # The object the verb is defined on (or matched via dspec)
args                  # List of positional args passed to the verb
kwargs                # Dict of keyword args
```
