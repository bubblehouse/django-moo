"""
Management command: moo_reset

Reset the game world for a bootstrap to a fixture snapshot:
1. Load the saved world fixture (restoring object locations and properties).
2. Clear ``zstate_*`` properties on Player avatars on the active site.

The clear is scoped to **player avatars only** so bootstrap-level ``zstate_*``
data on world objects (e.g. ZIL ``<LTABLE>`` content on ``$zork_sdk``) survives
the reset; otherwise reset would force a follow-up ``moo_init --sync`` to
re-create those tables.

Player accounts and their non-zstate properties are preserved.

Usage:
    manage.py moo_reset --bootstrap zork1
    manage.py moo_reset --bootstrap zork1 --hostname zork.local
    manage.py moo_reset --bootstrap zork1 --fixture path/to/world_state.json
"""

import json
import logging

from django.contrib.sites.models import Site
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from moo.core.code import ContextManager
from moo.core.managers import get_default_site
from moo.core.models import Object, Player, Property

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Reset a game world to its initial state from a fixture."

    def add_arguments(self, parser):
        parser.add_argument(
            "--bootstrap",
            type=str,
            required=True,
            help="Bootstrap name (e.g. zork1).",
        )
        parser.add_argument(
            "--hostname",
            type=str,
            default=None,
            help="Hostname of the Site to reset (defaults to Site SITE_ID).",
        )
        parser.add_argument(
            "--fixture",
            type=str,
            default=None,
            help=("Path to the world state fixture (default: moo/bootstrap/<bootstrap>/world_state.json)."),
        )
        parser.add_argument(
            "--keep-player-state",
            action="store_true",
            default=False,
            help="Skip clearing player zstate_* properties (useful for debugging).",
        )

    def handle(self, *args, **options):
        bootstrap = options["bootstrap"]
        hostname = options["hostname"]
        fixture = options["fixture"]
        keep_player_state = options["keep_player_state"]
        if fixture is None:
            fixture = f"moo/bootstrap/{bootstrap}/world_state.json"

        if hostname:
            try:
                site = Site.objects.get(domain=hostname)
            except Site.DoesNotExist as exc:
                raise CommandError(f"No Site with domain={hostname!r}") from exc
        else:
            site = get_default_site()
        ContextManager.set_site(site)

        # Read the fixture so we know which Object PKs are coming in. The save
        # command stripped site_id from them; we re-apply the active site
        # post-load so cross-deployment portability works.
        try:
            with open(fixture, encoding="utf-8") as f:
                fixture_rows = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            raise CommandError(f"Failed to read fixture {fixture}: {exc}") from exc
        loaded_object_pks = {row["pk"] for row in fixture_rows if row["model"] == "core.object"}

        self.stdout.write(f"Loading world state from {fixture} ...")
        try:
            call_command("loaddata", fixture, verbosity=0)
        except Exception as exc:
            raise CommandError(f"Failed to load fixture {fixture}: {exc}") from exc
        if loaded_object_pks:
            Object.global_objects.filter(pk__in=loaded_object_pks).update(site=site)
        self.stdout.write("  World state restored.")

        if not keep_player_state:
            deleted_count = _clear_player_zstate(site)
            self.stdout.write(f"  Cleared {deleted_count} player zstate_* properties on site {site.domain}.")
        else:
            self.stdout.write("  Skipped player zstate clear (--keep-player-state).")

        self.stdout.write(self.style.SUCCESS("Reset complete."))


def _clear_player_zstate(site) -> int:
    """
    Delete ``zstate_*`` properties on Player avatars for the given site.

    Bootstrap-level ``zstate_*`` properties on world objects (ZIL tables on
    ``$zork_sdk``, etc.) are intentionally untouched — they are static data
    seeded by ``moo_init`` and would otherwise need a follow-up
    ``moo_init --sync`` to recover.
    """
    avatar_pks = Player.objects.filter(site=site, avatar__isnull=False).values_list("avatar_id", flat=True)
    result = Property.objects.filter(origin_id__in=list(avatar_pks), name__startswith="zstate_").delete()
    return result[0]
