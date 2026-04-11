# pylint: disable=imported-auth-user
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from ...models import Object, Player


class Command(BaseCommand):
    help = "Attach a Django user to an avatar in the game."

    def add_arguments(self, parser):
        parser.add_argument("username", type=str, help="Name of the user to enable MOO access for.")
        parser.add_argument("avatar", type=str, help="Name of the Avatar to grant to the user.")
        parser.add_argument(
            "--wizard",
            action="store_true",
            help="Optionally set the user as a wizard (superuser) inside the game.",
        )
        parser.add_argument(
            "--hostname",
            default=None,
            help="Hostname of the Site to associate the player with (defaults to Site 1).",
        )

    def handle(self, username, avatar, wizard=False, hostname=None, **kwargs):  # pylint: disable=arguments-differ
        from django.contrib.sites.models import Site
        from django.conf import settings as django_settings

        if hostname:
            site, _ = Site.objects.get_or_create(domain=hostname, defaults={"name": hostname})
        else:
            site = Site.objects.get(pk=getattr(django_settings, "SITE_ID", 1))

        avatar_obj = Object.global_objects.get(name=avatar, unique_name=True, site=site)
        user = User.objects.get(username=username)
        player, created = Player.objects.get_or_create(avatar=avatar_obj, site=site, defaults=dict(user=user, wizard=wizard))
        if not created:
            player.user = user
            player.wizard = wizard
            player.save()
