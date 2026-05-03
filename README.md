# DjangoMOO

> "LambdaMOO on Django"

![release](https://gitlab.com/bubblehouse/django-moo/-/badges/release.svg)
![pipeline](https://gitlab.com/bubblehouse/django-moo/badges/main/pipeline.svg?ignore_skipped=true&job=test)
![coverage](https://gitlab.com/bubblehouse/django-moo/badges/main/coverage.svg?job=test%3Acoverage)
![quality](https://bubblehouse.gitlab.io/django-moo/badges/lint.svg)
![docs](https://readthedocs.org/projects/django-moo/badge/?version=latest)

DjangoMOO is a MOO server built on Python and Django. A MOO is a persistent online text world
where objects — rooms, things, players — have properties and verbs (methods) that define how
they behave. Those verbs are written in Python and run in a sandboxed execution environment,
so the world itself is programmable by its inhabitants.

The design follows the LambdaMOO model where it makes sense: a parsed command line, verb
dispatch through the caller's inventory and location, object inheritance, and a permission
system. The implementation is independent — no MOO bytecode, no C — just Python and Django.

**[Documentation](https://django-moo.readthedocs.io/)** |
**[GitLab](https://gitlab.com/bubblehouse/django-moo)** |
**[GitHub mirror](https://github.com/bubblehouse/django-moo)** |
**[PyPI](https://pypi.org/project/django-moo/)**

## What's included

- A LambdaMOO-inspired parser with full dobj/iobj preposition support
- Objects, Properties, Verbs, and a ManyToMany inheritance hierarchy backed by PostgreSQL
- A RestrictedPython verb sandbox with and integrated permissions system and extensive testing
- A default bootstrap world: rooms, exits, containers, players, a lighting system, in-world mail,
  and an object placement system
- Browser playable with no client required, or via plain SSH client
- Full support for MUDlet and other MUD clients using [sshelnet](https://gitlab.com/bubblehouse/sshelnet) helper
- Django admin for browsing and editing the world's objects, properties, and verb source
- Docker for self-hosting with `docker compose up`

## Quick Start

```bash
git clone https://gitlab.com/bubblehouse/django-moo
cd django-moo
docker compose up
```

Bootstrap the database and create your first wizard:

```bash
docker compose run webapp manage.py migrate
docker compose run webapp manage.py collectstatic
docker compose run webapp manage.py moo_init
docker compose run webapp manage.py createsuperuser --username wizard
docker compose run webapp manage.py moo_enableuser --wizard wizard Wizard
```

Connect at <https://localhost/> and log in with the account you just created.

## Interfaces

### MUD Clients

A Mudlet package in [`extras/mudlet/`](https://gitlab.com/bubblehouse/django-moo/-/tree/main/extras/mudlet) provides one-click
setup for MUD-client users. Mudlet has no native SSH support, so the package
bundles a managed [sshelnet](https://gitlab.com/bubblehouse/sshelnet) launcher
that bridges Mudlet's plain-TCP connection to the server's SSH port. It also
ships a setup wizard (`dmsetup`) and a generic-mapper bridge that subscribes
to GMCP `Room.Info` events and feeds them into Mudlet's bundled mapper.

![Mudlet Client Example](https://gitlab.com/bubblehouse/django-moo/-/raw/main/docs/images/mudlet-client-example.png)

The server speaks GMCP, MSSP, MSP, EOR, and CHARSET, so other clients
(TinTin++, MUSHclient, Blightmud) work too, though without the bundled
mapper integration, or automatic sshelnet setup. MXP is not implemented.

### Web (WebSocket SSH)

The server is accessible through a browser-based SSH client at `/`. No SSH client needed.

![WebSSH Client Example](https://gitlab.com/bubblehouse/django-moo/-/raw/main/docs/images/webssh-client-example.png)

![WebSSH Editor Example](https://gitlab.com/bubblehouse/django-moo/-/raw/main/docs/images/webssh-editor-example.png)

### SSH

Direct SSH access is also available.

```bash
ssh -p 8022 yourname@localhost
```

![SSH Client Example](https://gitlab.com/bubblehouse/django-moo/-/raw/main/docs/images/ssh-client-example.png)

Hit `Ctrl-D` to disconnect.

#### Changing your password and managing SSH keys

Credentials are managed from inside the world with in-game verbs rather than
the Django admin:

- `@password` — interactively changes your password. Prompts for the old
  password, then the new one twice for confirmation. Wizards may leave the old
  password blank to perform an administrative reset.
- `@keys` — lists your currently registered SSH public keys.
- `@add-key <public-key>` — registers a new SSH public key. The key name is
  taken from the comment field automatically.
- `@remove-key <index>` — removes a key by its index from `@keys`.

Once a key is registered, reconnecting with `ssh -p 8022 yourname@localhost`
skips the password prompt.

### Django Admin

A full Django admin interface is available at `/admin` for managing objects, properties,
verbs, and users.

![Django Admin Example](https://gitlab.com/bubblehouse/django-moo/-/raw/main/docs/images/django-admin-example.png)

## Attributions

### LambdaCore

This package is derived from the LambdaMOO and LambdaCore documentation, including the
LambdaCore Programmer's Manual and the LambdaMOO Programmer's Manual. The code was written
without reading the original LambdaCore source; it is an independent reimplementation based
on documented behavior and conventions.

Various verbs have been modified from their LambdaCore equivalents to better fit a Pythonic
codebase: output uses `print()` rather than return values, property access follows Django ORM
patterns, and permission idioms have been updated to account for differences in how this
server dispatches verbs compared to LambdaMOO.

DjangoMOO could not have happened without the work of the following authors:

- *LambdaCore Database User's Manual* (LambdaMOO 1.3, April 1991)
  Mike Prudence (blip), Simon Hunt (Ezeke), Floyd Moore (Phantom),
  Kelly Larson (Zaphod), Al Harrington (geezer)

- *LambdaCore Programmer's Manual* (LambdaMOO 1.8.0p6, Copyright 1991)
  Mike Prudence (blip), Simon Hunt (Ezeke), Floyd Moore (Phantom),
  Kelly Larson (Zaphod), Al Harrington (geezer)

- *LambdaMOO Programmer's Manual* (LambdaMOO 1.8.0p6, March 1997)
  Pavel Curtis (Haakon / Lambda)

### Zork 1

The optional `zork1` bootstrap (`moo/bootstrap/zork1/`) is a derivative work
of the Zork 1 source released under the MIT License by Microsoft / Activision
Publishing, Inc. in 2025. Its license and full attribution live in
`moo/bootstrap/zork1/LICENSE`; the rest of this project is AGPL-3.0.
Upstream source: <https://github.com/the-infocom-files/zork1>. Zork is a
registered trademark of Activision Publishing, Inc.; django-moo is not
affiliated with, endorsed by, or sponsored by Microsoft or Activision.
