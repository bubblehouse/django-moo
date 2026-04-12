"""
Management command: moo_save_state

Dumps the world state for a bootstrap (rooms, objects, properties, verb names,
and aliases) to a Django fixture file that can be used by moo_reset to restore
the world to a clean state.

Usage:
    manage.py moo_save_state --bootstrap zork1 --output moo/bootstrap/zork1/world_state.json
"""

import json
import logging

from django.core.management.base import BaseCommand, CommandError
from django.core.serializers import serialize
from django.db.models import Q

from moo.core.models import Object, Property, VerbName, Alias

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
            "--output",
            type=str,
            default=None,
            help="Output fixture file path (default: moo/bootstrap/<bootstrap>/world_state.json).",
        )

    def handle(self, *args, **options):
        bootstrap = options["bootstrap"]
        output = options["output"]
        if output is None:
            output = f"moo/bootstrap/{bootstrap}/world_state.json"

        # Find the root class objects for this bootstrap
        try:
            zork_room = Object.objects.get(name="Zork Room")
            zork_thing = Object.objects.get(name="Zork Thing")
            zork_container = Object.objects.get(name="Zork Container")
            zork_sdk = Object.objects.get(name="Zork SDK")
        except Object.DoesNotExist as exc:
            raise CommandError(
                f"Bootstrap root objects not found — run moo_init --bootstrap {bootstrap} first.\nMissing: {exc}"
            ) from exc

        # Collect all descendant objects of the zork root classes
        root_pks = {zork_room.pk, zork_thing.pk, zork_container.pk, zork_sdk.pk}
        world_objects = _collect_descendants(root_pks)
        world_pks = {obj.pk for obj in world_objects}

        log.info("Collecting state for %d world objects ...", len(world_pks))

        # Collect related data
        properties = Property.objects.filter(Q(origin_id__in=world_pks) & ~Q(name__startswith="zstate_"))
        verb_names = VerbName.objects.filter(verb__origin_id__in=world_pks)
        aliases = Alias.objects.filter(object_id__in=world_pks)

        # Serialize to fixture format
        all_querysets = [
            ("core.Object", world_objects),
            ("core.Property", list(properties)),
            ("core.VerbName", list(verb_names)),
            ("core.Alias", list(aliases)),
        ]

        fixture_data = []
        for _, queryset in all_querysets:
            serialized = json.loads(serialize("json", queryset))
            fixture_data.extend(serialized)

        with open(output, "w", encoding="utf-8") as f:
            json.dump(fixture_data, f, indent=2)

        self.stdout.write(
            self.style.SUCCESS(f"Saved {len(world_pks)} objects, {len(list(properties))} properties to {output}")
        )


def _collect_descendants(root_pks: set) -> list:
    """
    Collect all objects descended from the given root PKs via the parents
    ManyToMany relationship. Uses an iterative BFS to avoid recursion limits.
    """
    visited = set(root_pks)
    queue = list(root_pks)
    while queue:
        batch = queue[:200]
        queue = queue[200:]
        children = Object.objects.filter(parents__id__in=batch).exclude(pk__in=visited).values_list("pk", flat=True)
        new_pks = set(children)
        visited.update(new_pks)
        queue.extend(new_pks)
    return list(Object.objects.filter(pk__in=visited))
