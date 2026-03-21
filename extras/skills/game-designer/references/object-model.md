# DjangoMOO Object Model

## Core Parent Classes

| Class | Use for | Gets you |
|---|---|---|
| `$thing` | Portable objects (items, tools, props) | take/drop verbs, description |
| `$container` | Openable/closable containers (chests, cabinets, boxes, bags) | `open`/`close`/`put`/`take` verbs, `open` state, optional key lock; child of `$thing` so it's portable by default |
| `$furniture` | Fixed objects players can sit on (chairs, couches, benches, boulders, crates) | immovable (take fails), `sit`/`stand` verbs, customizable `*_msg` properties |
| `$note` | Anything with readable text: signs, menus, letters, plaques, books, bulletin boards | `read`/`edit`/`erase` verbs, optional read-lock; portable by default (add `moveto` returning `False` to fix in place) |
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
- `take_failed_msg` — shown to player when take fails
- `otake_failed_msg` — shown to room when take fails
- `drop_succeeded_msg` — shown to player on successful drop
- `odrop_succeeded_msg` — shown to room on successful drop
- `drop_failed_msg` — shown to player when drop fails
- `odrop_failed_msg` — shown to room when drop fails

All values use `pronoun_sub` format codes: `%N` = actor name, `%t` = object name. Override per-instance to customize flavor.

## `$furniture` Message Properties

`$furniture` inherits all `$thing` `_msg` properties plus:

- `sit_succeeded_msg` — shown to player when they sit (default: `"You sit on %t."`)
- `osit_succeeded_msg` — shown to room when player sits (default: `"%N sits on %t."`)
- `sit_failed_msg` — shown to player if they try to sit when already sitting on this piece (default: `"You are already sitting on %t."`)
- `stand_succeeded_msg` — shown to player when they stand up (default: `"You stand up from %t."`)
- `ostand_succeeded_msg` — shown to room when player stands (default: `"%N stands up from %t."`)
- `stand_failed_msg` — shown to player if `stand <furniture>` doesn't match what they're sitting on (default: `"You aren't sitting on %t."`)

### `$furniture` and Build-Time Placement

`$furniture` has a `moveto` verb that returns `False` — this is what makes players unable to pick it up. **This same verb also blocks `moveto()` calls from admin build code.** If the build script uses `lookup(N).moveto(lookup("Room"))`, `$furniture` objects will silently remain in the void.

The fix is to use direct Django model assignment, which bypasses the verb system:

```python
# WRONG — $furniture's moveto verb returns False, object stays in void
@eval "from moo.sdk import lookup; lookup(45).moveto(lookup(\"The Bar\"))"

# CORRECT — direct field assignment bypasses all verbs
@eval "from moo.sdk import lookup; obj = lookup(45); room = lookup(\"The Bar\"); obj.location = room; obj.save()"
```

`build_from_yaml.py` uses the correct approach for all object placement.

### Making Unusual Furniture Feel Right

Any object that shouldn't be moved and can plausibly be sat on is a candidate for `$furniture`. Flavor text can signal how comfortable (or not) it is:

```
# A hard bench
@edit property sit_succeeded_msg on "wooden bench" with "You sit on the wooden bench. It's not exactly comfortable."
@edit property osit_succeeded_msg on "wooden bench" with "%N settles onto the wooden bench with a wince."

# A boulder outside
@edit property sit_succeeded_msg on "mossy boulder" with "You perch on the boulder. Cold stone, but it'll do."
@edit property take_failed_msg on "mossy boulder" with "The boulder isn't going anywhere."

# A luxurious chair
@edit property sit_succeeded_msg on "velvet armchair" with "You sink into the velvet armchair. Heavenly."
@edit property stand_succeeded_msg on "velvet armchair" with "You reluctantly stand up from the velvet armchair."
```

The `take_failed_msg` property is particularly useful for explaining *why* something can't be moved — whether it's bolted down, too heavy, or simply absurd to pick up.

## `$container` — Openable Containers

`$container` is a child of `$thing`. Use it for any object that holds other objects and can be opened and closed: treasure chests, cabinets, safes, drawers, toolboxes, backpacks.

**Built-in verbs:**
- `open <container>` — sets state to open
- `close <container>` — sets state to closed
- `put <obj> in <container>` / `insert <obj> in <container>` — places an item inside (only when open)
- `get <obj> from <container>` / `take <obj> from <container>` — retrieves an item (only when open)
- `@lock_for_open <container> with <key>` — requires the key to open

**Key properties:**
- `open` (bool, default `false`) — current open/closed state
- `open_key` (null or key expression) — if set, container requires the matching key to open
- `opaque` (bool, default `false`) — if `true`, contents are hidden when container is closed

**YAML example (portable container):**

```yaml
- name: "leather satchel __hash_suffix__"
  parent: "$container"
  description: "A worn leather satchel with a brass clasp."
  aliases: ["satchel", "bag"]
  obvious: true
```

**Fixed containers** (cabinets, built-in drawers, a heavy safe) should use `$container` as the parent and add a `moveto` verb that returns `False` — same pattern as `$thing`-based immovable objects, but you keep all the open/close/put/take behavior:

```yaml
- name: "oak cabinet __hash_suffix__"
  parent: "$container"
  description: "A tall oak cabinet with iron hinges."
  aliases: ["cabinet"]
  obvious: true

verbs:
  - verb: "moveto"
    object: "oak cabinet __hash_suffix__"
    room: "Study"
    code: |
      #!moo verb moveto --on "oak cabinet __hash_suffix__"
      return False
```

Set a descriptive `take_failed_msg` so the player knows why they can't move it:

```
@edit property take_failed_msg on "oak cabinet" with "The cabinet is built into the wall."
```

**Do not use `$furniture` for containers.** `$furniture` adds `sit`/`stand` verbs and doesn't give you `open`/`close`. A chest or cabinet should always be `$container`, even if it's also immovable.

## `$note` — Readable Text Objects

Use `$note` for anything with readable text content: signs, menus, letters, plaques, books, newspapers, bulletin boards, wanted posters. The player types `read <object>` to see the text.

**Built-in verbs:**
- `read <note>` (also `r <note>`) — prints the `text` property to the player
- `edit <note>` — opens the in-game text editor to change the text
- `erase <note>` — clears the text
- `@lock_for_read <note> with <key>` — restricts reading to players holding the key

**Key properties:**
- `text` (string) — the content shown when the player reads it. Set via `@edit property text on "sign" with "..."` or via `@edit` to use the interactive editor.
- `read_key` (null or key expression) — if set, reading requires the matching key

**Signs and fixed notices** are the most common use case. They are portable by default (child of `$thing`), so add a `moveto` verb returning `False` to fix them in place:

```yaml
- name: "welcome sign __hash_suffix__"
  parent: "$note"
  description: "A wooden sign hangs by the entrance."
  aliases: ["sign", "wooden sign", "notice"]
  obvious: true

verbs:
  - verb: "moveto"
    object: "welcome sign __hash_suffix__"
    room: "Entrance"
    code: |
      #!moo verb moveto --on "welcome sign __hash_suffix__"
      return False
```

Set the text content with `@edit property`:

```
@edit property text on "welcome sign" with "Welcome to Springfield. Population: Dwindling."
```

**Room descriptions with signs:** The room description should only say the sign is there. Let the player choose to read it. Do not embed the sign text in the room description unless it is essential to understanding the room.

```
# WRONG — room description contains the sign text
The entrance features a sign that reads: "No shirt, no shoes, no service."

# CORRECT — room description acknowledges the sign; player reads it themselves
A hand-lettered sign hangs beside the entrance.
```

**Aliases matter for signs.** If the room has multiple readable objects, give each specific aliases so `read sign` always resolves unambiguously:

```yaml
aliases: ["sign", "wooden sign", "notice"]   # entrance welcome sign
aliases: ["menu", "chalkboard menu", "board"] # bar menu
aliases: ["letter", "envelope", "note"]       # letter on desk
```

## Immovable but Not Sittable

If an object should be fixed in place but doesn't make sense to sit on (a statue, a machine, a tree), use `$thing` as the parent and override its `moveto` verb to return `False`:

```
@create "stone statue" from "$thing"
@edit verb moveto on "stone statue"
```

Verb body:
```python
return False
```

Then set a descriptive `take_failed_msg`:

```
@edit property take_failed_msg on "stone statue" with "The statue is far too heavy to move."
```

This blocks `take`, `give`, and any other movement without adding `sit`/`stand` verbs.
