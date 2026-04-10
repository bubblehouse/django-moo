# Building Your First Room

This tutorial walks you through creating a room, connecting it to the world with exits, and populating it with objects — all without writing any Python code. By the end you'll have a new location players can visit, a container object they can open, and an alias that lets them refer to it by multiple names.

## Prerequisites

Before you start:

- You have an SSH connection to the server as a player with builder access
- You understand the basics covered in {doc}`player-basics` (navigation, `look`, inventory)

To check that you have quota (permission to create objects):

```
$ @quota
Object quota: 9 of 10 remaining.
```

If your quota is 0, ask a wizard to increase it.

## Step 1: Orient yourself

```
$ look
The Laboratory(#3)
A cavernous laboratory filled with gadgetry...

Obvious exits: none
```

```
$ @rooms
Rooms owned by YourName:
  none
```

No rooms yet. Let's fix that.

## Step 2: Create a room

You don't own The Laboratory, so you can't dig exits from it. Instead, create a room object and place it in the void — with no location — then teleport into it.

```
$ @create "The Storeroom" from $room in void
Created The Storeroom(#22).
```

The `in void` clause is required. Without it, the room would be created inside your inventory, and `@move me to` won't teleport you into a room that's contained inside you. Now move yourself into it:

```
$ @move me to "The Storeroom"
Moved Wizard to The Storeroom.
```

```
$ look
The Storeroom(#22)
No description set.

Obvious exits: none
```

You're in your new room. You own it, so you can dig exits from here.

## Step 3: Describe the room

```
$ @describe here as "A dusty storeroom with shelves of forgotten things lining the walls. A single bulb flickers overhead."
Description set.
```

Type `look` to confirm:

```
$ look
The Storeroom(#22)
A dusty storeroom with shelves of forgotten things lining the walls. A single bulb
flickers overhead.

Obvious exits: none
```

`here` is a shorthand that refers to your current room. You can also use the room name or its `#N` ID.

## Step 4: Wire exits

Now connect the storeroom to The Laboratory. `@dig` creates a new room and exit in one step. `@tunnel` creates an exit to a room that already exists — that's what you want here.

Create a south exit from the storeroom back to The Laboratory:

```
$ @tunnel south to "The Laboratory"
Dug an exit south to "The Laboratory(#3)".
```

Now go to The Laboratory and add the north exit pointing back:

```
$ @move me to "The Laboratory"
Moved Wizard to The Laboratory.

$ @tunnel north to "The Storeroom"
Dug an exit north to "The Storeroom(#22)".
```

Verify the connection:

```
$ go north
The Storeroom(#22)
A dusty storeroom with shelves...

Obvious exits: south
```

Both exits are wired. You're back in the storeroom — continue building from here.

## Step 5: Create an object

`@create` makes a new object from a parent class. The syntax is:

```
@create "<name>" from <parent>
```

Common parents: `$thing` (a basic object), `$container` (holds items), `$furniture` (something to sit on).

```
$ @create "battered wooden crate" from $container
Created battered wooden crate(#23).
```

The new object appears in your inventory. Type `look` to see it listed under contents:

```
$ look
The Storeroom(#22)
...
Contents: battered wooden crate
```

## Step 6: Describe and alias the object

Set a description:

```
$ @describe crate as "A battered battered wooden crate with iron corner brackets. The lid is loose."
Description set.
```

Add aliases so players can refer to it by shorter names:

```
$ @alias crate as "box"
Alias added: box.

$ @alias crate as "wooden box"
Alias added: wooden box.
```

Now `look at crate`, `look at box`, and `look at wooden box` all work.

## Step 7: Make the object visible

By default, newly created objects are not listed when players `look` at the room — they're `non-obvious`. Make the crate show up:

```
$ @obvious crate
battered wooden crate is now obvious.
```

Now `look` shows it:

```
$ look
The Storeroom(#22)
A dusty storeroom with shelves...

Contents: battered wooden crate
Obvious exits: south
```

To hide an object again later, use `@nonobvious`.

## Step 8: Put something inside the crate

Create something to put inside it:

```
$ @create "brass gear" from $thing
Created brass gear(#24).
```

Now drop it into the crate:

```
$ drop gear in crate
You put brass gear in crate.
```

Confirm with:

```
$ look in crate
The crate contains:
  a brass gear
```

## Step 9: Check your work

```
$ @rooms
Rooms owned by YourName:
  The Storeroom(#22)
```

```
$ @quota
Object quota: 4 of 10 remaining.
```

Five objects consumed quota: the storeroom, two exits, the crate, and the brass gear.

## What just happened

Every `@`-prefixed command is a verb on your player object or on the system object. `@create` instantiates a child of the named parent class; `in void` places it with no location instead of in your inventory. `@move me to` teleports your avatar to any room you can name. `@tunnel` creates a `$exit` instance pointing to an existing room and wires the source and destination. `@dig` does the same but also creates a new room in one step. `@obvious` sets the `obvious` property on the object to `true`, which the `look` verb reads when assembling the room's contents list.

None of this required writing code — you're authoring a world by calling built-in verbs.

## Where to go next

- {doc}`first-verb` — Add a custom Python verb to your crate (e.g. a `search` command that prints what you find)
- {doc}`../reference/objects` — Full reference for object classes, parent hierarchies, and the `$container` / `$furniture` / `$thing` distinctions
- {doc}`../how-to/bootstrapping` — Make your rooms and objects part of a bootstrap dataset that survives a database reset
- {doc}`../reference/permissions` — Lock your room so only certain players can enter
