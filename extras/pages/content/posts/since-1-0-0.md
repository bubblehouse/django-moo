+++
date = '2026-05-30T00:00:00-04:00'
draft = false
title = 'What Changed Since 1.0.0'
+++

When 1.0 dropped, I planned a release announcement rollout that was focused on the MUD community, largely through r/MUD. This did NOT go well. The overwhelming consensus was that any lack of traditional MUD client support was a complete and total deal-breaker, and anyone who thought it was not important to completely implement support for screen readers and telnet IAC was an idiot completely unaware of the needs of the community. Also, I was a soulless AI-bro who was ruining everything.

1.0.0 shipped in mid-April. The six weeks since have been less about new world content and more about how people (and programs) actually connect to a world and read what it sends back. Most of the attention went to client handling: traditional MUD clients, screen-reader accessibility, and the protocols and proxies that let a non-xterm client get a usable session.

## Client handling

This is where most of the work since 1.0.0 landed, and the loudest feedback with it. Three fronts: getting a usable session into a traditional MUD client, making the output stream legible to a screen reader, and bridging an SSH-only server to telnet-only clients, by hand or through Mudlet.

### Accessibility

Screen-reader support landed in 1.3.0, and it answered the accessibility complaint the r/MUD thread kept returning to. A MOO is a stream of text arriving at unpredictable times, and a screen reader needs to know where one logical chunk ends and the next begins. The shell now emits OSC 133 markers around prompts and command output so an assistive client can announce boundaries instead of running everything together. The same release added an `a11y` verb for toggling assistive behavior per player, and gating on the `[ERROR]` prefix so error text is distinguishable from ordinary output.

### Traditional MUD clients

DjangoMOO's prompt is a full prompt_toolkit application — great over SSH to a real terminal, useless to a traditional MUD client that expects a plain telnet line discipline. 1.2.0 added a raw mode for exactly those clients: a stripped-down line handler, a `get_client_mode()` helper so verbs can adapt their output, and inline forms of the editor-driven verbs (`@edit`, `@gripe`) so you can pass content on the command line instead of dropping into a full-screen editor the client can't render.

1.4.0 was the big protocol release. It added a telnet IAC subnegotiation library, wired into the SSH session and prompt lifecycle, as the foundation for everything out-of-band. On top of that came GMCP: `send_oob`, `send_gmcp`, and `play_sound` in the SDK, an IRE-style `room_info_payload` for `Room.Info`, and GMCP events emitted from `say`, `emote`, `page`, `whisper`, `confunc`, and `exit.move`. A client that speaks GMCP can drive a sidebar, a map, or sound triggers off live world events. The bundled `djangomoo` Mudlet package, for one, feeds `Room.Info` straight into Mudlet's generic mapper. The same release added an external-editor handoff over GMCP (`Editor.Start`, `Editor.Save`, `Editor.Cancel`) so a capable client can pop verb or note editing into its own native editor instead of the in-band one.

### Bridging telnet clients with sshelnet

That still leaves one gap: DjangoMOO speaks SSH, and a classic MUD client speaks plain telnet with no encryption layer. TinTin++, MUSHclient, and most of the rest never will. The bridge has to live outside the engine, and that's [sshelnet](https://gitlab.com/bubblehouse/sshelnet), a small Go proxy that listens on a local TCP port and forwards each connection over SSH with a raw-termios PTY, so telnet IAC, GMCP, MSSP, and MTTS round-trip cleanly. The terminal type it announces decides the experience: `xterm-256-basic` trips DjangoMOO into raw mode for a MUD client, plain `xterm` keeps the full UI for a real terminal.

### The Mudlet package

Mudlet gets a turnkey path. The `djangomoo` package wraps everything above: it manages the sshelnet launcher for you (downloading and running the right binary as a child process), runs a `dmsetup` wizard for host and auth, feeds GMCP `Room.Info` into Mudlet's bundled generic mapper, and routes `@edit` and the other editor verbs to your local editor over the GMCP editor protocol. From the player's seat it's install, `dmsetup`, connect. The [package README](https://gitlab.com/bubblehouse/django-moo/-/blob/main/extras/mudlet/README.md) has the full walkthrough, including editor configuration and mapping.

## Multiple worlds on one deployment

1.6.0 added multi-universe support built on Django Sites (issue #18). One deployment can now host several independent worlds, and an SSH connection is routed to the right one by a suffix on the username. 1.8.0 followed up by keeping cross-site object references intact when `moojson` deserializes outside a site context, which matters as soon as you're moving data between worlds.

## NPCs and daemons

The bootstrap world grew some life in 1.10.0. There's a `$daemon` class with scheduled-tick verbs and an `@daemon` wizard command for registering them, backed by scheduled-task lifecycle helpers in the SDK that JSON-encode their periodic-task arguments. On top of that sit `$npc` and `$wanderer` classes with a personality-daemon hook and an `@npc` command, so a builder can stand up a wandering character without writing the scheduling plumbing.

## Where this leaves things

The throughline across all of it is reach: a screen-reader user, a Mudlet player, and an SSH purist should all get a world that behaves the way their client expects, and an operator should be able to run more than one world without standing up more than one deployment. None of it changed the engine's shape: same parser, same RestrictedPython sandbox, same object model as 1.0.0.

- GitLab: [gitlab.com/bubblehouse/django-moo](https://gitlab.com/bubblehouse/django-moo)
- Docs: [django-moo.readthedocs.io](https://django-moo.readthedocs.io/)
- Full changelog: [CHANGELOG.md](https://gitlab.com/bubblehouse/django-moo/-/blob/main/CHANGELOG.md)
