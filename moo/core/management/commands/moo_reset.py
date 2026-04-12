"""
Management command: moo_reset

Resets the game world for a bootstrap to its clean initial state by:
1. Loading the saved world fixture (restoring object locations and properties)
2. Clearing all zstate_* properties from all player objects

This is non-destructive to player accounts — only game state is cleared.

Usage:
    manage.py moo_reset --bootstrap zork1
    manage.py moo_reset --bootstrap zork1 --fixture path/to/world_state.json
"""

import logging

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from moo.core.models import Object, Property

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
        fixture = options["fixture"]
        keep_player_state = options["keep_player_state"]
        if fixture is None:
            fixture = f"moo/bootstrap/{bootstrap}/world_state.json"

        # Step 1: restore world object state via loaddata
        self.stdout.write(f"Loading world state from {fixture} ...")
        try:
            call_command("loaddata", fixture, verbosity=0)
        except Exception as exc:
            raise CommandError(f"Failed to load fixture {fixture}: {exc}") from exc
        self.stdout.write("  World state restored.")

        # Step 2: clear per-player zstate_* properties
        if not keep_player_state:
            deleted_count = _clear_player_zstate()
            self.stdout.write(f"  Cleared {deleted_count} player zstate_* properties.")
        else:
            self.stdout.write("  Skipped player zstate clear (--keep-player-state).")

        self.stdout.write(self.style.SUCCESS("Reset complete."))


def _clear_player_zstate() -> int:
    """
    Remove all zstate_* properties from every object in the world.

    zstate_* properties are only written to player objects, so this is
    equivalent to clearing per-player state without needing to locate a
    specific player class (which differs between bootstrap datasets).
    """
    result = Property.objects.filter(name__startswith="zstate_").delete()
    # result is a tuple: (count, {model: count})
    return result[0]
