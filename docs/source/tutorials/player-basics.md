# Getting Started as a Player

This tutorial walks you through connecting to a DjangoMOO server, finding your way around, picking things up, and talking to other players. By the end you'll know how to navigate the world, manage your inventory, communicate with others, and customize your character.

The example output below was captured with a plain SSH client. A MUD client (e.g. Mudlet) renders the same output with colors, a compass display, and other niceties — but every command shown here works the same way regardless of client.

## Prerequisites

Before you start:

- A DjangoMOO server is running and you have an account
- You have connected with an appropriate client (web, ssh, mud client, etc)

## Step 1: Orient yourself

Type `look` and press Enter:

```
↖ ↑ ↗  The Laboratory
← ↕ →  A cavernous laboratory filled with gadgetry of every kind, this seems
↙ ↓ ↘  like a dumping ground for every piece of dusty forgotten equipment a mad
       scientist might require.
You see a heavy wooden workbench here.
Newman, Cliff, and Player are here.
```

The compass on the left shows which directions have exits — `↑`/`→`/`↙` etc.; `↕` means you can go both up and down. The room name and description follow. Below that come two contents lines: `You see <X> here.` for objects, and `<names> are here.` for other characters.

Type `@who` to see everyone currently connected:

```
Connected players:
  Wizard [The Laboratory]
```

## Step 2: Navigate

To see exactly which directions have exits and where they go, use `@exits`:

```
Exits defined for this room:
- south from The Laboratory (Aliases: south) to Grand Foyer (#34)
- north from The Laboratory (Aliases: north) to Boiler Annex (#155)
- east from The Laboratory (Aliases: east) to Cooling Intake (#199)
- west from The Laboratory (Aliases: west) to Exhaust Chamber (#204)
- ...
```

To move, type a direction — `go north`, `go east`, `go down`, etc., or just the direction alone (`east`):

```
$ go east
You leave #22 (The Laboratory).
You arrive at #199 (Cooling Intake).
↖ ↑ ↗  Cooling Intake
←   →  A drafty, industrial corridor designed to pull fresh air into the
↙ ↓ ↘  mansion's mechanical heart.
You see a heavy iron tool crate here.
```

Whenever you arrive somewhere new, the room is described automatically. To return to your starting point at any time:

```
$ home
↖ ↑ ↗  The Laboratory
← ↕ →  A cavernous laboratory filled with gadgetry of every kind, this seems
↙ ↓ ↘  like a dumping ground for every piece of dusty forgotten equipment a mad
       scientist might require.
You see a heavy wooden workbench here.
Newman, Cliff, and Player are here.
```

Your home defaults to the room you started in. You can change it later (see Step 7).

## Step 3: Examine things

`look at <name>` shows the description of an object or another player:

```
$ look at Cliff
Not much to see here.
They are sleeping.
```

(`Not much to see here.` is the default when an object has no description set yet.)

The second line is the player's connection status — sleeping, awake and alert, or idle.

```
$ look at workbench
Not much to see here.
```

If you want more information about an object — its owner, parents, aliases, contents, and verbs — use `examine <name>` (it's a discovery tool, not a basic player command, but worth knowing):

```
$ examine workbench
heavy wooden workbench (#176 ) is owned by Joiner (#27).
Parents:
  Generic Furniture (#14)
Aliases:
wooden workbench, workbench
Not much to see here.
```

To see what's inside a container, use `look in <container>`. There's no permanent demo container in The Laboratory, so let's make one. The next two sections both build on this little prop:

```
$ @create "crate" from $container
Created #890 (crate) in your inventory.
Transmuted #890 (crate) to #6 (Generic Container).

$ drop crate
You drop crate.

$ @obvious crate
crate is now obvious.

$ open crate
You open the container.
```

Now you have an open crate sitting in The Laboratory. `look in crate`:

```
Not much to see here.
It is empty.
```

(Containers default to closed; `open crate` is required before you can put things into it or take things out. You'll see what happens when you try below.)

## Step 4: Pick things up and manage your inventory

Make something to put in the crate:

```
$ @create "brass key" from $thing
Created #891 (brass key) in your inventory.
Transmuted #891 (brass key) to #13 (Generic Thing).
```

To put it in the crate, use `put`:

```
$ put brass key in crate
You placed brass key in crate.
```

Verify with `look in crate`:

```
Not much to see here.
Contents:
  brass key
```

To take something out of a container, `take <name> from <container>`:

```
$ take brass key from crate
You took brass key from crate.
```

To see what you're carrying:

```
$ inventory
You are carrying:
brass key
polishing cloth
```

Or just `inv` for short. To put something on the floor, `drop <name>`:

```
$ drop brass key
You drop brass key.
```

To pick it back up, `take <name>`:

```
$ take brass key
You take brass key.
```

Names match exactly (or by alias). `drop key` won't find your `brass key` unless you've added a `key` alias to it (see {doc}`building-rooms` for `@alias`).

## Step 5: Talk to others

To say something out loud to everyone in the room:

```
$ say Hello, Lab!
You: Hello, Lab!
```

Everyone else in the room sees:

```
Wizard: Hello, Lab!
```

To send a private message to a player anywhere in the world, use `page <player> with <message>`:

```
$ page Cliff with Are you there?
Your message has been sent.
```

Cliff (if connected) sees:

```
You sense that Wizard is looking for you in The Laboratory.
Wizard pages, "Are you there?"
```

If the recipient isn't connected, you'll see `<player> is not currently logged in.` instead.

To whisper privately to a player in the same room, `whisper <message> to <player>`:

```
$ whisper testing to Cliff
You whisper to Cliff: testing
```

## Step 6: Read and send mail

Mail lives in a per-player inbox. `@mail` shows your inbox:

```
Your mailbox (2 messages, 1 unread) — page 1 of 1:

      From                Subject                                   Date
 ---  ------------------  ----------------------------------------  ------------
  1*  Wizard              Re: Welcome                               Apr 26 18:32
  2   Wizard              Welcome                                   Apr 26 18:32

* = unread
Type '@mail <n>' to read a message.
```

`*` marks unread messages. To read a specific message:

```
$ @mail 2
Message #2 from Wizard — Apr 26 18:32
Subject: Welcome
────────────────────────────────────────────────────────────────────────────────
Hi there. This is a test message.
```

To send a new message, type `@send Wizard` (replacing `Wizard` with whoever you're writing to). The full-screen editor opens, pre-filled with `Subject:`. Type a subject on the first line, leave a blank line, then write your message body. `Ctrl+S` then `Y` to send. You'll see:

```
Message sent to Wizard.
```

To reply to a message you've read, type `@reply 1` (with the message number you want to reply to). The editor opens with a pre-filled subject (`Re: <original>`) and the original message quoted in the body.

Both `@send` and `@reply` also accept a `with "<text>"` argument for scripted use. The editor flow is the normal interactive path.

## Step 7: Customize your character

To set your description (what others see when they `look at` you):

```
$ @describe me as "A newcomer with curious eyes and ink-stained fingers."
Description set for #5 (Wizard)
```

To set your pronouns:

```
$ @gender male
Gender set to male, and pronouns updated.
```

Options: `male`, `female`, `neuter`, `plural` (gender-neutral they/them).

To change your password, use the `@password` verb. It prompts for old and new passwords interactively:

```
$ @password
Old password:
New password:
Confirm:
Password changed.
```

To set your home to your current location:

```
$ @sethome
Your home has been set to your current location.
```

Now `home` will always bring you back here.

## What just happened

Every command you typed was parsed by the server into a verb call. `look` runs a verb on the room object. `say` runs a verb on the room you're in. `take` and `drop` run verbs on the object being moved. Behind each command is a few lines of Python that check permissions, modify state, and send output back to you and others.

This is the core of MOO: objects have verbs, players issue commands, the server dispatches to the right verb, and the world updates.

## Where to go next

- {doc}`building-rooms` — Create rooms, objects, and exits
- {doc}`first-verb` — Write Python code that runs as a command
- {doc}`../how-to/ssh-key-management` — Set up SSH key authentication so you don't need a password
