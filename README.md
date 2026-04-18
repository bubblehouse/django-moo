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
- A RestrictedPython verb sandbox with a security-audited allowlist (55+ known escape vectors tested)
- A default bootstrap world: rooms, exits, containers, players, a lighting system, in-world mail,
  and an object placement system
- Browser playable with no client required via WebSocket SSH
- Django admin for browsing and editing the world's objects, properties, and verb source
- Docker + Helm for self-hosting with `docker compose up`
- moo-agent: autonomous LLM agents that inhabit the world via SSH (see below)

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

### Web (WebSocket SSH)

The server is accessible through a browser-based SSH client at `/`. No SSH client needed.

![WebSSH Client Example](https://gitlab.com/bubblehouse/django-moo/-/raw/main/docs/images/webssh-client-example.png)

![WebSSH Editor Example](https://gitlab.com/bubblehouse/django-moo/-/raw/main/docs/images/webssh-editor-example.png)

### SSH

Direct SSH access is also available. Associate an SSH key with your account in the Django
admin to skip the password prompt.

```bash
ssh -p 8022 yourname@localhost
```

![SSH Client Example](https://gitlab.com/bubblehouse/django-moo/-/raw/main/docs/images/ssh-client-example.png)

Hit `Ctrl-D` to disconnect.

### Django Admin

A full Django admin interface is available at `/admin` for managing objects, properties,
verbs, and users.

![Django Admin Example](https://gitlab.com/bubblehouse/django-moo/-/raw/main/docs/images/django-admin-example.png)

## AI agents with moo-agent

[moo-agent](https://gitlab.com/bubblehouse/moo-agent) is a companion package that connects
autonomous LLM agents to DjangoMOO via SSH. Each agent has:

- A SOUL.md personality file (plain text, version-controlled)
- Persistent memory that accumulates across sessions
- Tools for interacting with the world: move, look, take, drop, read, send mail, and more
- Multi-agent orchestration via a Foreman coordination layer

Backends: Anthropic (Claude), AWS Bedrock, and LM Studio for local models.

```bash
pip install moo-agent
moo-agent init --name MyAgent --host localhost --port 8022 --user myagent ./my-agent
moo-agent run ./my-agent
```

Full moo-agent docs: <https://moo-agent.readthedocs.io/>

## LambdaCore attributions

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
