# DjangoMOO Object Model

## Core Parent Classes

| Class | Use for | Gets you |
|---|---|---|
| `$thing` | Inert objects, furniture, containers | take/drop verbs, description |
| `$note` | Readable documents, menus, tabs, letters | read/edit/burn verbs |
| `$player` | NPCs with dialogue | tell/announce infrastructure, full player API |
| `$room` | Rooms (created by `@dig`, not `@create`) | contents, exits, announce |
| `$exit` | Exits (created by `@dig`/`@tunnel`) | go verb, dest property |

## Designing Parent Classes

When 4+ objects share the same behavior (same verbs, same properties), create a Generic parent class first:

```
@create "Generic Beer Glass" from "$thing"
@edit verb drink on "Generic Beer Glass"
@edit property full on "Generic Beer Glass" with true
@edit property brand on "Generic Beer Glass" with "unknown"

# Then instances inherit drink/full/brand automatically:
@create "a pint of Duff" from "Generic Beer Glass"
@edit property brand on "a pint of Duff" with "Duff"
```

This keeps verbs in one place. Fixing a bug in `drink` fixes it for all glass instances.

## NPC Design

NPCs use `$player` as parent to get the full messaging infrastructure (tell, announce, etc.). They do not have a `Player` auth record and cannot log in.

```
@create "Generic Tavern NPC" from "$player"
@edit verb speak on "Generic Tavern NPC"
@edit property lines on "Generic Tavern NPC" with ["Hello.", "Goodbye."]

@create "Moe" from "Generic Tavern NPC"
@move "Moe" to "Moe's Tavern"
@describe "Moe" as "A surly bartender."
@edit property lines on "Moe" with ["Yeah?", "What'll it be?", "We're closing.", "Get out."]
```

**Note on gender**: `@gender` only sets the caller's own pronouns — it cannot be used to set an NPC's gender. To set NPC gender, set the `gender` property directly and the individual pronoun properties (`her`, `him`, `his`, etc.) on the NPC object. Skip gender setup entirely if the NPCs don't need pronoun-aware messages.

## Exits

`@dig <dir> to "<room>"` creates:
- A new room
- A one-way exit from current location in `<dir>`

The exit object has:
- `dest` property: the destination room Object
- Verb aliases for the direction word (e.g., `go north` and just `north`)

`@tunnel <dir> to "<room>"` adds a reverse exit from the current location (after navigating to the new room).

**Exit connectivity check pattern** (used in test verbs):
```python
exits = room.get_property("exits")  # or room.exits.all()
for exit_obj in exits:
    dest = exit_obj.get_property("dest")
    # dest is the destination Room object
```

## Properties vs. Verbs

- **Properties** hold data: description (`description`), state (`full`, `occupied`, `locked`), content (`lines`, `outcomes`, `brand`), references (`key`, `dest`)
- **Verbs** hold behavior: `drink`, `sit`, `speak`, `throw`, `read`, `pull`

Properties set via `@edit property name on "obj" with <json-value>` where the value is JSON-encoded:
- String: `with "text"`
- Number: `with 42`
- Boolean: `with true` or `with false`
- List: `with ["a", "b", "c"]`
- null: `with null`

## `$sys` / System Object

The system object (`$sys` or `sys` in verbs) holds references to global parent classes. From SSH, you cannot use `sys.set_property`. Reference parents by name via `lookup()`:

```python
# In a verb:
beer_glass_class = lookup("Generic Beer Glass")
glass = create("a pint", parents=[beer_glass_class], location=context.player)
```

## Object Naming Conventions

- Generic classes: `"Generic <Type>"` (e.g., `"Generic Beer Glass"`, `"Generic Tavern NPC"`)
- Room instances: Proper names (e.g., `"Moe's Tavern"`, `"The Back Room"`)
- NPC instances: Character names (e.g., `"Moe"`, `"Barney"`)
- Object instances: `"a <thing>"` or `"the <thing>"` (e.g., `"the jukebox"`, `"a dartboard"`)

## Disambiguation with `#N` References

When multiple objects share the same name (e.g., 4 "bar stool" instances), any command that references them by name will fail with `AmbiguousObjectError`. Use the `#N` object ID instead:

```
# Fails if multiple "bar stool" objects exist:
@describe "bar stool" as "..."

# Works every time:
@describe #34 as "Wobbly bar stool with cracked vinyl."
@edit verb sit on #34 with "print('You sit.')"
@move #34 to "The Bar"
```

The `#N` number comes from `@create` output: `Created #34 (bar stool)`. In build scripts, capture it with `re.search(r'(#\d+)', output)`.

`#N` refs are never quoted in MOO commands. Named string refs are always quoted.

## Checking Object State

```python
# List verbs on an object (from SSH):
@show "Generic Beer Glass"

# List _msg properties:
@messages "a pint of Duff"

# From inside a verb:
try:
    v = this.get_verb("drink")
except exceptions.NoSuchVerbError:
    print("No drink verb found.")
```

## Contents and Location

```python
# All objects in a room
room.contents.all()

# A player's inventory
context.player.contents.all()

# An object's current location
obj.location
```

## `$thing` Message Properties

Objects descended from `$thing` inherit these `_msg` properties (set via `@edit property`):

- `take_succeeded_msg` — shown to player on successful take
- `otake_succeeded_msg` — shown to room on successful take
- `drop_succeeded_msg` — shown to player on successful drop
- `odrop_succeeded_msg` — shown to room on successful drop

Override per-instance to customize pickup/drop text flavor.
