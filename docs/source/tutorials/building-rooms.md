# Building Your First Room

This tutorial walks you through creating a room, connecting it to the world with exits, and populating it with objects — all without writing any Python code. By the end you'll have a new location players can visit, a container object they can open, and an alias that lets them refer to it by multiple names.

## Prerequisites

Before you start:

- An connection to the server as a player with builder access
- You understand the basics covered in {doc}`player-basics` (navigation, `look`, inventory)

To check that you have quota (permission to create objects):

```
$ @quota
Your quota is 803.
```

A wizard or builder typically starts with a generous quota. If yours is `0`, ask a wizard to increase it.

## Step 1: Orient yourself

```
$ look
↖ ↑ ↗  The Laboratory
← ↕ →  A cavernous laboratory filled with gadgetry of every kind, this seems
↙ ↓ ↘  like a dumping ground for every piece of dusty forgotten equipment a mad
       scientist might require.
You see a heavy wooden workbench here.
Newman, Cliff, and Player are here.
```

```
$ @rooms
Rooms in the world:
  #9  Mail Distribution Center
  #22  The Laboratory
  #23  The Agency
  #34  Grand Foyer
  ...
```

`@rooms` lists every room currently in the world. It's a discovery aid for builders so you can see what's already there before you start creating.

## Step 2: Create a room

The fastest way to add a room *and* wire an exit to it in one go is `@dig`:

```
$ @dig northeast to "The Studio"
Dug an exit northeast to "The Studio" (#897).
```

This creates a new room called The Studio (you own it), then digs a `northeast` exit from your current room to The Studio. The number in parentheses is the new room's database ID.

Walk into your new room:

```
$ go northeast
You leave #22 (The Laboratory).
You arrive at #897 (The Studio).
↖ ↑ ↗  The Studio
←   →  There's not much to see here.
↙ ↓ ↘
```

The compass shows you have one exit (back the way you came); the description is the default placeholder.

## Step 3: Describe the room

Set a description with `@describe here as "..."`:

```
$ @describe here as "A bright artist's studio with paint-spattered floorboards. Tall windows let in the afternoon light."
Description set for #897 (The Studio)
```

`look` to confirm:

```
$ look
↖ ↑ ↗  The Studio
←   →  A bright artist's studio with paint-spattered floorboards. Tall windows
↙ ↓ ↘  let in the afternoon light.
```

`here` is shorthand for your current room. You can also pass the room name (`@describe "The Studio" as "..."`) or its `#N` ID.

## Step 4: Wire the return exit

`@dig` made a one-way exit (northeast from The Laboratory). To get back, you need an exit going the other way. From inside The Studio:

```
$ @tunnel southwest to "The Laboratory"
Tunnelled an exit southwest to "The Laboratory" (#22).
```

`@tunnel` is the same verb as `@dig`, but instead of creating a new room it wires the exit to a room that already exists (looked up by name). Now you can travel both ways:

```
$ go southwest
You leave #897 (The Studio).
You arrive at #22 (The Laboratory).
...

$ go northeast
You leave #22 (The Laboratory).
You arrive at #897 (The Studio).
...
```

If a direction is already used you'll get `There is already an exit in that direction.` — pick a free one.

### `@burrow`: dig, walk, tunnel in one shot

`@burrow` runs the full sequence above as a single atomic command — forward exit, new room, move you into it, return exit:

```
$ @burrow north to "The Watchtower"
Dug north to The Watchtower (#81).
Tunnelled south back to The Laboratory (#19).
You are now in The Watchtower (#81).
```

The return direction is inferred from the forward direction's opposite (`north`/`south`, `east`/`west`, etc.). If one direction is already used, `@burrow` reports the conflict and bails out cleanly — no partial wiring left behind.

### Ownership of created rooms and exits

Rooms and exits created by `@dig`, `@tunnel`, and `@burrow` are owned by **you** (the caller), not by the wizard who happens to be running the session and not by whichever player class the verb is attached to. This matters because owners are the only ones who can freely modify a room's description, name, or aliases — so a builder who runs `@dig` ends up with a room they can edit immediately, without a follow-up `@chown`. The same rule applies to `@create`.

## Step 5: Create an object

`@create` makes a new object from a parent class. The syntax is:

```
@create "<name>" from <parent>
```

Common parents: `$thing` (a basic object), `$container` (holds items), `$furniture` (something to sit on).

```
$ @create "wooden box" from $container
Created #899 (wooden box) in your inventory.
Transmuted #899 (wooden box) to #6 (Generic Container).
```

The new object lands in your inventory. Drop it so it's part of the room:

```
$ drop wooden box
You drop wooden box.
```

## Step 6: Describe and alias the object

Set a description:

```
$ @describe wooden box as "A small wooden box, the lid loose enough to lift."
Description set for #899 (wooden box)
```

Add aliases so players can refer to it by shorter names:

```
$ @alias wooden box as "box"
Added alias 'box' to #899 (wooden box)
```

Now `look at box`, `look at wooden box`, and `look at #899` all work. Aliases are case-insensitive and you can add as many as you like.

## Step 7: Make the object visible

By default, newly created objects are not listed when players `look` at the room — they're "non-obvious". Make the box show up:

```
$ @obvious wooden box
wooden box is now obvious.
```

Now `look` shows it under "You see ... here.":

```
$ look
↖ ↑ ↗  The Studio
←   →  A bright artist's studio with paint-spattered floorboards. Tall windows
↙ ↓ ↘  let in the afternoon light.
You see a wooden box here.
```

To hide an object again later, use `@nonobvious`.

## Step 8: Put something inside the box

Create something to put inside it:

```
$ @create "brass gear" from $thing
Created #900 (brass gear) in your inventory.
Transmuted #900 (brass gear) to #13 (Generic Thing).
```

Containers default to *closed* — open the box first:

```
$ open box
You open the container.
```

Now put the gear in:

```
$ put brass gear in box
You placed brass gear in wooden box.
```

Confirm with:

```
$ look in box
A small wooden box, the lid loose enough to lift.
Contents:
  brass gear
```

## Step 9: Check your work

```
$ @quota
Your quota is 795.
```

Five objects consumed quota: the studio, two exits (one each way), the box, and the brass gear.

## What just happened

Every `@`-prefixed command is a verb on your player object or on a system object. `@dig` instantiates a new room and a new `$exit` pointing at it; `@tunnel` skips room creation and just wires an exit to an existing room. `@create` instantiates a child of the named parent class and drops it in your inventory. `@describe`, `@alias`, and `@obvious` set properties on the object that the `look` verb consults when assembling its output.

None of this required writing code — you're authoring a world by calling built-in verbs.

## Where to go next

- {doc}`first-verb` — Add a custom Python verb to your box (e.g. a `search` command that prints what you find)
- {doc}`../reference/objects` — Full reference for object classes, parent hierarchies, and the `$container` / `$furniture` / `$thing` distinctions
- {doc}`../how-to/bootstrapping` — Make your rooms and objects part of a bootstrap dataset that survives a database reset
- {doc}`../reference/permissions` — Lock your room so only certain players can enter
