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

## Step 2: Dig a new room

`@dig` creates a new room and wires an exit to it. The syntax is:

```
@dig <direction> to "<Room Name>"
```

```
$ @dig north to "The Storeroom"
Exit north created to The Storeroom(#22).
```

The number after `#` is the database ID of your new room. Now go there:

```
$ go north
The Storeroom(#22)
No description set.

Obvious exits: none
```

You're in. The `Obvious exits: none` line means there's no way out yet — we'll fix that in the next step.

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

## Step 4: Wire the return exit

Right now you can't get back. Run `@dig` again from inside the storeroom to create a south exit back to The Laboratory:

```
$ @dig south to "The Laboratory"
Exit south created to The Laboratory(#3).
```

Verify:

```
$ @exits
Exits from The Storeroom:
  south -> The Laboratory(#3)
```

Go back and confirm the connection works both ways:

```
$ go south
The Laboratory(#3)
...
Obvious exits: north
```

The north exit now appears because you created it in Step 2. Go back north to continue building.

```
$ go north
```

## Step 5: Create an object

`@create` makes a new object from a parent class. The syntax is:

```
@create "<name>" from <parent>
```

Common parents: `$thing` (a basic object), `$container` (holds items), `$furniture` (something to sit on).

```
$ @create "wooden crate" from $container
Created wooden crate(#23).
```

The new object appears in your inventory. Type `look` to see it listed under contents:

```
$ look
The Storeroom(#22)
...
Contents: wooden crate
```

## Step 6: Describe and alias the object

Set a description:

```
$ @describe crate as "A battered wooden crate with iron corner brackets. The lid is loose."
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
wooden crate is now obvious.
```

Now `look` shows it:

```
$ look
The Storeroom(#22)
A dusty storeroom with shelves...

Contents: wooden crate
Obvious exits: south
```

To hide an object again later, use `@nonobvious`.

## Step 8: Put something inside the crate

Take something from your inventory and drop it into the crate. If your inventory is empty, first pick something up from the Lab — go south, grab an object, come back north.

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
Object quota: 7 of 10 remaining.
```

Two objects consumed quota: the storeroom and the crate (exits don't count toward most quota limits).

## What just happened

Every `@`-prefixed command is a verb on your player object or on the system object. `@dig` creates a new `$room` instance and a `$exit` instance, wires the source and destination, and places the exit in the current room. `@create` instantiates a child of the named parent class and places it in your inventory. `@obvious` sets the `obvious` property on the object to `true`, which the `look` verb reads when assembling the room's contents list.

None of this required writing code — you're authoring a world by calling built-in verbs.

## Where to go next

- {doc}`first-verb` — Add a custom Python verb to your crate (e.g. a `search` command that prints what you find)
- {doc}`../reference/objects` — Full reference for object classes, parent hierarchies, and the `$container` / `$furniture` / `$thing` distinctions
- {doc}`../how-to/bootstrapping` — Make your rooms and objects part of a bootstrap dataset that survives a database reset
- {doc}`../reference/permissions` — Lock your room so only certain players can enter
