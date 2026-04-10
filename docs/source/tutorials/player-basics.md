# Getting Started as a Player

This tutorial walks you through connecting to a DjangoMOO server, finding your way around, picking things up, and talking to other players. By the end you'll know how to navigate the world, manage your inventory, communicate with others, and customize your character.

## Prerequisites

Before you start:

- A DjangoMOO server is running and you have an account
- You have an SSH client installed

To connect, run (substituting your server's hostname and your username):

```bash
ssh -p 8022 YourName@localhost
```

You'll see a welcome message and then a `$` prompt.

## Step 1: Orient yourself

Type `look` and press Enter:

```
The Laboratory(#3)
A cavernous laboratory filled with gadgetry, workbenches, and the faint smell of
ozone. It is here that new things are tested before being released into the world.

Contents: Wizard
Obvious exits: none
```

The first line is the room name and database ID. Below that is the description. `Contents` lists other players and objects in the room. `Obvious exits` lists directions you can travel.

Type `@who` to see everyone currently connected:

```
Wizard (connected)
```

## Step 2: Navigate

To move, type a direction — `go north`, `go south`, `go east`, `go west`, `go up`, `go down` — or just the direction alone: `north`, `south`, etc.

```
$ go north
There is no exit in that direction.
```

If there are no exits yet, you can't go anywhere. To see which directions have exits:

```
$ @exits
Exits from The Laboratory:
  none
```

To return home from wherever you end up:

```
$ home
You teleport home.
```

Your home defaults to the room you started in. You can change it later (see Step 7).

## Step 3: Examine things

`look` shows the room. To look at a specific object in the room or in your inventory:

```
$ look at Wizard
Wizard is a tall figure in a long coat.
```

You can also use `examine`:

```
$ examine workbench
An imposing steel workbench, its surface scarred by years of experiment.
```

`look in <container>` shows what's inside a container object:

```
$ look in crate
The crate contains:
  a brass gear
  a length of copper wire
```

## Step 4: Pick things up and manage your inventory

To pick something up:

```
$ take gear
You pick up brass gear.
```

To see what you're carrying:

```
$ inventory
You are carrying:
  a brass gear
```

Or just `i` for short. To put something down:

```
$ drop gear
You drop brass gear.
```

To put an item inside a container:

```
$ drop gear in crate
You put brass gear in crate.
```

To take something out of a container:

```
$ take gear from crate
You take brass gear from crate.
```

## Step 5: Talk to others

To speak to everyone in the room:

```
$ say Hello!
You say, "Hello!"
```

Everyone else in the room sees:

```
Wizard says, "Hello!"
```

To send a private message to a player anywhere in the world:

```
$ page Wizard Are you there?
Your message has been sent.
```

Wizard receives:

```
You sense that YourName is looking for you in The Laboratory.
YourName pages: Are you there?
```

To whisper to a player in the same room:

```
$ whisper Wizard I have a secret.
You whisper to Wizard, "I have a secret."
```

## Step 6: Read and send mail

`@mail` shows your inbox:

```
$ @mail
  1  Cliff    [Apr 10] It's a little-known fact...
  2* Newman   [Apr 10] And another thing, Clavin
```

Messages marked `*` are unread. To read a message:

```
$ @mail 2
From: Newman
Date: Apr 10
Subject: And another thing, Clavin

...
```

To send a new message:

```
$ @send Wizard Hello from a new player
Subject: Hello from a new player

Type your message. End with a period on its own line.
This is my first mail.
.
Message sent.
```

To reply to a message you've read:

```
$ @reply 2 Thanks, Newman.
Message sent.
```

## Step 7: Customize your character

To set your description (what others see when they `look at` you):

```
$ @describe me as "A newcomer with curious eyes and ink-stained fingers."
Description set.
```

To set your pronouns:

```
$ @gender male
Gender set to male. (he/him/his)
```

Options: `male`, `female`, `neuter`, `plural`.

To change your password:

```
$ @password
Old password: ...
New password: ...
Confirm: ...
Password changed.
```

To set your home to your current location:

```
$ @sethome
Home set to The Laboratory(#3).
```

Now `home` will always bring you back here.

## What just happened

Every command you typed was parsed by the server into a verb call. `look` runs a verb on the room object. `say` runs a verb on your player object. `take` and `drop` run verbs on the object being moved. Behind each command is a few lines of Python that check permissions, modify state, and send output back to you and others.

This is the core of MOO: objects have verbs, players issue commands, the server dispatches to the right verb, and the world updates.

## Where to go next

- {doc}`building-rooms` — Create rooms, objects, and exits
- {doc}`first-verb` — Write Python code that runs as a command
- {doc}`../how-to/ssh-key-management` — Set up SSH key authentication so you don't need a password
