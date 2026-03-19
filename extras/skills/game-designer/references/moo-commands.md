# MOO Wizard Build Commands

## Room and Exit Commands

### `@dig`
```
@dig <direction> to "<room name>"
```
Creates a new room and a one-way exit from the current location in `<direction>`. The new room becomes accessible via that exit. Returns the name of the new exit object.

Example:
```
@dig north to "The Bar"
@dig south to "The Dartboard Corner"
```

### `@tunnel`
```
@tunnel <direction> to "<room name>"
```
Creates an exit from the current location to an *existing* room. Use this for reverse exits after `@dig`.

Example:
```
# After digging north to "The Bar", go to The Bar and run:
@tunnel south to "The Main Room"
```

## Object Commands

### `@create`
```
@create "<name>" from "<parent>"
```
Creates a new object instance with the given parent. Places it in your inventory.

Examples:
```
@create "Generic Tavern NPC" from "$player"
@create "Generic Beer Glass" from "$thing"
@create "Moe" from "Generic Tavern NPC"
@create "a pint of Duff" from "Generic Beer Glass"
```

### `@describe`
```
@describe "<object>" as "<text>"
```
Sets the description property. Use `here` for the current room.

Examples:
```
@describe here as "A dimly lit bar with sticky floors and neon signs."
@describe "Moe" as "A surly bartender with a perpetual scowl."
```

### `@move`
```
@move "<object>" to "<location>"
```
Moves an object to a room or container.

Examples:
```
@move "Moe" to "Moe's Tavern"
@move "the jukebox" to "Moe's Tavern"
```

### `@gender`
```
@gender "<object>" as <gender>
```
Sets pronouns. Options: `male`, `female`, `neuter`, `either`, `royal`.

Example:
```
@gender "Moe" as male
```

### `@lock`
```
@lock "<exit>" with <key-expression>
```
Locks an exit. The key expression is evaluated as a boolean.

Example:
```
@lock "the back door" with $wizard
```

## Property and Verb Editing

### `@edit verb`
```
@edit verb <name> on "<object>"
@edit verb <name> on "<object>" with "<code>"
```
Opens the verb editor for a named verb on an object, creating it if it doesn't exist. The `with` form sets code inline without opening the editor — useful for one-liners.

Examples:
```
@edit verb drink on "Generic Beer Glass"
@edit verb speak on "Moe" with "print('Moe grunts at you.')"
```

### `@edit property`
```
@edit property <name> on "<object>"
@edit property <name> on "<object>" with <json-value>
```
Opens the property editor, creating the property if it doesn't exist. The `with` form sets a JSON-encoded value inline.

Examples:
```
@edit property lines on "Moe" with ["Yeah?", "What'll it be?", "We're closing."]
@edit property full on "Generic Beer Glass" with true
@edit property brand on "Generic Beer Glass" with "Duff"
```

## Inspection Commands

### `@show`
```
@show "<object>"
```
Lists all verbs and properties defined directly on an object.

### `@messages`
```
@messages "<object>"
```
Lists all `_msg` properties (take/drop/look messages) on an object and its parents.

### `@test-<name>`
```
@test-<name>
```
Runs the environment verification verb. Must be placed on `$programmer`.

## Navigation Tip

After `@dig`, you remain in the original room. To reach the new room:
```
go north    # or whatever direction you dug
```
Then use `@tunnel` to add the return exit, and `@describe here` for the new room.
