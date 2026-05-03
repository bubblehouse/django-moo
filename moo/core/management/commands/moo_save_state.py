"""
Management command: moo_save_state

Dumps the world state for a bootstrap (rooms, objects, properties, verb names,
and aliases) to a Django fixture file that can be used by moo_reset to restore
the world to a clean state.

Per-player ``zstate_*`` properties are excluded from the snapshot — those
accumulate during play and are cleared on reset, not restored. Bootstrap-level
``zstate_*`` (e.g. ZIL tables on ``$zil_sdk``) are kept.

The serialized rows have ``site_id`` stripped so the fixture is portable; the
current site is re-applied on load by ``moo_reset``.

Usage:
    manage.py moo_save_state --bootstrap zork1 [--hostname zork.local] [--output PATH]
"""

import json
import logging

from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand, CommandError
from django.core.serializers import serialize
from django.db.models import Q

from moo.core.code import ContextManager
from moo.core.managers import get_default_site
from moo.core.models import Alias, Object, Player, Property, VerbName

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Dump world object state for a bootstrap to a fixture file."

    def add_arguments(self, parser):
        parser.add_argument(
            "--bootstrap",
            type=str,
            required=True,
            help="Bootstrap name (e.g. zork1). Used to locate the class roots.",
        )
        parser.add_argument(
            "--hostname",
            type=str,
            default=None,
            help="Hostname of the Site to snapshot (defaults to Site SITE_ID).",
        )
        parser.add_argument(
            "--output",
            type=str,
            default=None,
            help="Output fixture file path (default: moo/bootstrap/<bootstrap>/world_state.json).",
        )

    def handle(self, *args, **options):
        bootstrap = options["bootstrap"]
        hostname = options["hostname"]
        output = options["output"]
        if output is None:
            output = f"moo/bootstrap/{bootstrap}/world_state.json"

        if hostname:
            try:
                site = Site.objects.get(domain=hostname)
            except Site.DoesNotExist as exc:
                raise CommandError(f"No Site with domain={hostname!r}") from exc
        else:
            site = get_default_site()
        ContextManager.set_site(site)

        # Find the root class objects for this bootstrap on the active site.
        # global_objects bypasses the SiteManager filter so we are explicit
        # about which universe we're snapshotting.  ``Zork Root`` is the
        # parent of every translated room/thing/container/actor/exit, so
        # walking its descendants captures the world.  ``ZIL SDK`` carries
        # the table data and isn't a Zork Root descendant — it's added
        # separately as a snapshot root.
        root_names = ("Zork Root", "ZIL SDK")
        try:
            roots = [Object.global_objects.get(name=n, site=site) for n in root_names]
        except Object.DoesNotExist as exc:
            raise CommandError(
                f"Bootstrap root objects not found on site {site.domain!r} — "
                f"run moo_init --hostname {site.domain} --bootstrap {bootstrap} first.\nMissing: {exc}"
            ) from exc

        # Collect all descendant objects of the bootstrap roots on this site.
        root_pks = {r.pk for r in roots}
        world_objects = _collect_descendants(root_pks, site)
        world_pks = {obj.pk for obj in world_objects}

        log.info("Collecting state for %d world objects on site %s ...", len(world_pks), site.domain)

        # Player avatar PKs in this universe — their zstate_* properties are
        # per-player game state and must NOT be snapshotted.
        player_avatar_pks = set(
            Player.objects.filter(site=site, avatar_id__in=world_pks).values_list("avatar_id", flat=True)
        )

        # Properties: include all on world objects EXCEPT zstate_* on player avatars.
        properties = Property.objects.filter(origin_id__in=world_pks).exclude(
            Q(origin_id__in=player_avatar_pks) & Q(name__startswith="zstate_")
        )
        verb_names = VerbName.objects.filter(verb__origin_id__in=world_pks)
        aliases = Alias.objects.filter(object_id__in=world_pks)

        # Serialize to fixture format. site_id is stripped from Object rows so
        # the fixture is portable across deployments — moo_reset re-applies
        # the current site at load time.
        fixture_data = []
        for serialized_qs in (world_objects, list(properties), list(verb_names), list(aliases)):
            for row in json.loads(serialize("json", serialized_qs)):
                if row["model"] == "core.object":
                    row["fields"].pop("site", None)
                fixture_data.append(row)

        with open(output, "w", encoding="utf-8") as f:
            json.dump(fixture_data, f, indent=2)

        self.stdout.write(
            self.style.SUCCESS(f"Saved {len(world_pks)} objects, {len(list(properties))} properties to {output}")
        )


def _collect_descendants(root_pks: set, site) -> list:
    """
    Collect all objects descended from the given root PKs via the parents
    ManyToMany relationship, scoped to ``site``. Iterative BFS.
    """
    visited = set(root_pks)
    queue = list(root_pks)
    while queue:
        batch = queue[:200]
        queue = queue[200:]
        children = (
            Object.global_objects.filter(parents__id__in=batch, site=site)
            .exclude(pk__in=visited)
            .values_list("pk", flat=True)
        )
        new_pks = set(children)
        visited.update(new_pks)
        queue.extend(new_pks)
    return list(Object.global_objects.filter(pk__in=visited, site=site))
