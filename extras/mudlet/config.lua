mpackage = [[djangomoo]]
author = [[DjangoMOO Project]]
title = [[DjangoMOO client integration for Mudlet.]]
description = [[# DjangoMOO

End-to-end Mudlet integration for [DjangoMOO](https://gitlab.com/bubblehouse/django-moo)
servers. Bundles three things:

- A managed [sshelnet](https://gitlab.com/bubblehouse/sshelnet) launcher
  that downloads the right release binary on first use and bridges
  Mudlet's TCP connection to the SSH server transparently.
- A setup wizard (`dmsetup`) that captures host/port/username/auth and
  writes the matching sshelnet profile.
- The original generic-mapper bridge: `gmcp.Room.Info` -> `map.prompt`
  -> `onNewRoom` -> Mudlet's bundled mapper pipeline.

## Quick start

1. `dmsetup host moo.example.com`
2. `dmsetup port 8022`
3. `dmsetup username yourname`
4. `dmsetup auth password` (or `key` / `agent`)
5. `dmconnect` -- prompts once per Mudlet session for the SSH password.

Subsequent reconnects in the same session reuse the cached password.
The SSH password is never written to disk; sshelnet receives it via the
`SSHELNET_PASSWORD` environment variable.

Run `dmstatus` to see current state, `dmupgrade` to refresh the bundled
sshelnet to the latest GitLab release.
]]
version = [[1.3.0]]
created = "2026-04-25T00:00:00+00:00"
icon = [[icon.png]]
sshelnet_pinned_version = [[v1.1.0]]
