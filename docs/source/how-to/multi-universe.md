# Run Multiple Universes on One Server

A single django-moo deployment can host independent worlds — separate
object hierarchies, separate player accounts, separate game state — by
serving each one from a different hostname. This is the "multi-universe"
or "multi-site" mode.

Each universe is a Django ``Site`` row. Every database query that goes
through {class}`moo.core.models.object.Object.objects` is scoped to the
active Site by the {class}`moo.core.managers.SiteManager`. Wizards are
scoped per Site by default; opt-in cross-universe rights go through the
{class}`moo.core.models.auth.UniversalWizard` table.

The SSH protocol has no equivalent of TLS SNI or HTTP `Host` (see
RFCs 4253/4254/8308), so the dialed hostname cannot reach the server
on its own. DjangoMOO resolves the active Site by either (a) a suffix
encoded in the SSH username — ``ssh user+sitedomain@host`` — or (b) an
interactive picker shown after authentication.

## Bootstrap a second universe

Each Site has its own copy of the System Object, Wizard, root classes,
and game state. To add a second universe pointing at hostname
``test.example.com``:

```bash
docker compose run webapp manage.py moo_init \
    --bootstrap default --hostname test.example.com
```

`--hostname` looks up (or creates) a `Site` row with that domain and
makes it the active site for the bootstrap run. Run `moo_init` again
with a different hostname (and a different `--bootstrap` if desired)
to add a third, fourth, etc.

The default site is `localhost` unless `SITE_ID` is set in Django
settings. Connections without an explicit hostname (or to a hostname
not registered in `Site.objects`) fall back to that default.

## Connect to a specific universe

### Direct SSH

Encode the Site domain in the SSH username with a `+` delimiter:

```bash
ssh -p 8022 alice+zork.example.com@your-host
```

The server splits `alice+zork.example.com` into the Django user
`alice` and the Site `zork.example.com`. Without a suffix, the server
prints the universes available to your account and prompts you to
pick one — useful the first time, but routine connections should use
the suffix to skip the prompt.

If the suffix names a Site that doesn't exist, the picker runs anyway
so you can fall back to a real universe.

### Webssh / browser

When you visit `https://zork.example.com/` (with a `Site` row that
matches that domain), the Django POST proxy reads the browser's
`Host` header and rewrites the SSH username to include the matching
suffix before handing the connection to webssh. The terminal prints
``Connected to universe: zork.example.com`` so you can confirm the
routing succeeded.

If the browser hostname doesn't match a `Site` row, no suffix is
injected and you'll see the picker (or the default site for
single-universe accounts).

## Per-site wizard accounts

By default, a wizard avatar in one universe is just a player in another.
Each `Player` row carries a `site` foreign key, and the unique
constraint on `(user, site)` allows the same Django `User` to have
distinct avatars in different universes.

Create a per-site wizard by bootstrapping that universe (`moo_init`
creates a `Wizard` Object on each fresh site) and then logging in via
the matching hostname.

## Cross-universe wizard rights

For a single Django user to act as wizard on every universe — useful for
operators — mark the user as a UniversalWizard:

```bash
docker compose run webapp manage.py moo_make_universal alice
```

On the next SSH connection to any site, if Alice doesn't have a Player
row for that site yet, the server auto-provisions a wizard avatar +
Player for her on that site. Existing avatars are not modified.

To revoke:

```bash
docker compose run webapp manage.py moo_make_universal alice --remove
```

`User.is_superuser` alone does not grant cross-universe rights —
universal wizard status is opt-in via this command.

## Site-scoped queries

`Object.objects`, `Property.objects`, and `Verb.objects` all go through
`SiteManager` and silently filter to the active site. To query across
sites — for diagnostics, migrations, or admin tooling — use
`Object.global_objects` (and the analogous globals on other models).

Inside a verb, the active site is whatever the calling player connected
to; you don't need to pass it explicitly. Inside management commands and
Celery tasks, use `code.ContextManager(player_or_wizard, ..., site=...)`
to set the active site for the duration of the block.

## When *not* to use multi-universe

Multi-universe is overkill for:

- A single game world with a development hostname and a production one;
  use Django settings (`ALLOWED_HOSTS`, etc.) instead, since both
  hostnames point at the same Site.
- "Areas" or "themed zones" within one game; those are just rooms
  parented appropriately.

It earns its complexity when you genuinely need separate persistent
worlds — one production game, one external dataset (the `zork1`
bootstrap shipped with moo-agent is one example), one private
playtest — each with independent objects and players.

## Diagnostic commands

Inspect the current site set:

```bash
docker compose run webapp manage.py shell
```

```python
>>> from django.contrib.sites.models import Site
>>> for s in Site.objects.all():
...     print(s.pk, s.domain, s.name)
```

Find every Player on a given site:

```python
>>> from moo.core.models.auth import Player
>>> Player.objects.filter(site__domain="zork.example.com")
```

List all UniversalWizard accounts:

```python
>>> from moo.core.models.auth import UniversalWizard
>>> UniversalWizard.objects.values_list("user__username", flat=True)
```
