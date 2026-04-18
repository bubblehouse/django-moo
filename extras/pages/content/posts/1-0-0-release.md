+++
date = '2026-04-18T00:00:00-04:00'
draft = false
title = 'DjangoMOO 1.0.0'
+++

DjangoMOO 1.0.0 is out. The release pipeline, Docker images, and documentation have been production-grade for a while — what kept this in 0.x was the world itself. There weren't enough built-in primitives to make something actually playable or worth building in. Getting there took long enough that it's worth writing up what's in the box.

## What ships

The core server has a LambdaMOO-style command parser with multiple preposition support, flexible verb dispatch, and an object model backed by PostgreSQL. Inherent ownership, ACLs, and a wizard/builder/programmer class hierarchy handle permissions. Verb execution is via RestrictedPython, with a sandbox hardened against known escape vectors.

The default world loaded by `moo_init` includes rooms, exits, containers, players, and generic things, plus a lighting system (`is_lit`, `alight`), an in-world mail system (`@mail`, `@send`, `@reply`, `@forward`), an object placement system (`@place` with hidden placements and surface grouping), and in-world text objects (books, post boards).

On the infrastructure side: Docker Compose handles local development and single-host deployments, with a Helm chart for Kubernetes if you want something more production-grade. GitLab CI drives automated releases — semantic versioning from commit history, packages to PyPI, images to the Docker registry. The world is accessible via direct SSH or through a browser-based WebSSH client with no additional setup. Django admin gives you a full object browser where you can inspect and edit any object, property, or verb source in the world. API documentation is published to ReadTheDocs via Sphinx.

## moo-agent

[moo-agent](https://gitlab.com/bubblehouse/moo-agent) shipped as a standalone package alongside this release. It connects LLM agents to a running DjangoMOO world via SSH. Each agent has a SOUL.md personality file, persistent memory, and tools for interacting with the world: moving between rooms, picking things up, reading books, sending in-world mail. A Foreman coordination layer handles multi-agent orchestration. Supported backends: Anthropic, AWS Bedrock, and LM Studio for local models.

Agents with appropriate permissions can author verbs that change how objects behave — they have write access to the world's logic, not just the ability to move through it.

## Links

- GitLab: [gitlab.com/bubblehouse/django-moo](https://gitlab.com/bubblehouse/django-moo)
- GitHub mirror: [github.com/bubblehouse/django-moo](https://github.com/bubblehouse/django-moo)
- Docs: [django-moo.readthedocs.io](https://django-moo.readthedocs.io/)
- moo-agent: [gitlab.com/bubblehouse/moo-agent](https://gitlab.com/bubblehouse/moo-agent)
