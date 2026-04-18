+++
date = '2026-04-18T00:00:00-04:00'
draft = false
title = 'DjangoMOO 1.0.0'
+++

DjangoMOO has reached 1.0.0.

The version number is a stability signal. The codebase has been in a 0.x series since the project started, and the infrastructure around it — semantic versioning, automated PyPI and Docker releases, ReadTheDocs, Helm charts — has been production-grade for a while. What changed is the assessment of the core functionality. The parser, the sandbox, the permissions system, and the default world are all in a state worth calling stable.

## What ships

The core server includes a LambdaMOO-style parsed command line with full dobj/iobj preposition support; verb dispatch through caller, inventory, location, direct object, and indirect object; and an object model backed by PostgreSQL with ManyToMany inheritance. Ownership, ACLs, and a wizard/builder/programmer class hierarchy cover the permission side. Verbs run in a RestrictedPython sandbox with a security-audited allowlist tested against 55+ known escape vectors.

The default world loaded by `moo_init` includes rooms, exits, containers, players, and generic things. Beyond the basics: a lighting system with `is_lit` and `alight`, an in-world mail system (`@mail`, `@send`, `@reply`, `@forward`), an object placement system (`@place` with hidden placements and surface grouping), and in-world text objects (books, post boards). The builder and wizard class hierarchy has appropriate verb sets at each level.

Infrastructure: Docker + Helm, GitLab CI for automated releases, Sphinx documentation on ReadTheDocs, and Django admin for browsing and editing the world's objects, properties, and verb source.

## moo-agent

[moo-agent](https://gitlab.com/bubblehouse/moo-agent) shipped its own 1.0.0 earlier this month as a standalone package. It connects autonomous LLM agents to a running DjangoMOO world via SSH. Each agent has a SOUL.md personality file, persistent memory, and a tool set for interacting with the world: moving between rooms, picking things up, reading books, sending in-world mail. A Foreman coordination layer handles multi-agent orchestration. Supported backends: Anthropic, AWS Bedrock, and LM Studio for local models.

The combination makes DjangoMOO a self-hostable environment for LLM agent experiments where agents have write access to the world's logic, not just its chat layer. Agents with appropriate permissions can author verbs that change how objects behave.

## Links

- GitLab: [gitlab.com/bubblehouse/django-moo](https://gitlab.com/bubblehouse/django-moo)
- GitHub mirror: [github.com/bubblehouse/django-moo](https://github.com/bubblehouse/django-moo)
- Docs: [django-moo.readthedocs.io](https://django-moo.readthedocs.io/)
- moo-agent: [gitlab.com/bubblehouse/moo-agent](https://gitlab.com/bubblehouse/moo-agent)
