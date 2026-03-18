# Verb Code Patterns

All verbs run inside the RestrictedPython sandbox.

**No shebang in SSH-edited verbs.** The `#!moo verb name --on $obj` shebang is only for bootstrap verb *files* in `moo/bootstrap/default_verbs/`. When you create a verb via `@edit verb <name> on "<obj>"` in an SSH session, the verb name and target are already registered by that command — the code body starts directly with imports.

## Imports

```python
from moo.sdk import context, create, lookup, invoke
from moo.sdk import NoSuchObjectError, NoSuchVerbError, NoSuchPropertyError
import time
```

Available restricted imports: `moo.sdk`, `re`, `datetime`, `time`, `hashlib`

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

## State Toggle (sit/stand, open/close, lock/unlock)

```python
from moo.sdk import context, NoSuchPropertyError

occupied = this.get_property("occupied")
if occupied:
    this.set_property("occupied", False)
    print("You stand up.")
    context.player.location.announce_all_but(context.player, f"{context.player.name} stands up.")
else:
    this.set_property("occupied", True)
    print("You sit down.")
    context.player.location.announce_all_but(context.player, f"{context.player.name} sits down.")
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
import time

lines = this.get_property("lines")
idx = int(time.time()) % len(lines)
msg = lines[idx]
print(f'{this.name} says, "{msg}"')
context.player.location.announce_all_but(context.player, f'{this.name} says, "{msg}"')
```

The `lines` property is a list of strings set via `@edit property lines on "NPC" with ["line1", "line2"]`.

## Random Outcome (dartboard, jukebox, slot machine)

```python
from moo.sdk import context
import time

outcomes = this.get_property("outcomes")
idx = int(time.time()) % len(outcomes)
result = outcomes[idx]
print(f"You throw. {result}")
context.player.location.announce_all_but(context.player, f"{context.player.name} throws a dart. {result}")
```

## Prank Call Pattern (phone booth, payphone)

```python
from moo.sdk import context
import time

names = this.get_property("names")
idx = int(time.time()) % len(names)
name = names[idx]
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
