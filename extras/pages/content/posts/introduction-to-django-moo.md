+++
date = '2026-03-21T13:54:06-04:00'
draft = false
title = 'Introduction to DjangoMOO'
+++

DjangoMOO is a programmable virtual world engine. You can think of it as a text-based game where the players can also modify and expand the game while playing it.

The classic text adventure gives you a fixed world: whatever rooms, objects, commands the author decided to support. A MOO goes further. Every object in the world — every room, item, even the players themselves — can have little programs attached called "verbs." A player with the right permissions can write @say hello today and tomorrow write a new verb that makes candles flicker when someone enters a room, or implements an in-world economy, or changes how the look command works for a specific object.

The original LambdaMOO (1990) was a research project at Xerox PARC that became a surprisingly rich social world precisely because its inhabitants could shape it. DjangoMOO is a modern reimplementation of that concept, built on the Django web framework with a Python execution sandbox so players can write Python code as verbs rather than the original MOO language. It runs a real SSH server so you connect with a terminal, but it also supports WebSSH so you can play in a browser.

The interesting engineering problem it solves: how do you let untrusted users execute arbitrary code inside your server without them escaping the sandbox, reading other players' data, or taking down the process? That turns out to be a surprisingly deep problem, which is why there's a 130-test security suite just for the verb execution layer.
