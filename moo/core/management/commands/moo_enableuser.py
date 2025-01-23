# pylint: disable=imported-auth-user
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from ...models import Object, Player


class Command(BaseCommand):
    help = "Attach a Django user to an avatar in the game."

    def add_arguments(self, parser):
        parser.add_argument(
            "username", type=str, help="Name of the user to enable MOO access for."
        )
        parser.add_argument(
            "avatar", type=str, help="Name of the Avatar to grant to the user."
        )
        parser.add_argument(
            "--wizard",
            action="store_true",
            help="Optionally set the user as a wizard (superuser) inside the game.",
        )

    def handle(
        self, username, avatar, wizard=False, **kwargs
    ):  # pylint: disable=arguments-differ
        avatar = Object.objects.get(name=avatar, unique_name=True)
        user = User.objects.get(username=username)
        if not getattr(user, "player", None):
            player = Player()
            player.save()
            user.player = player
        user.player.avatar = avatar
        user.player.wizard = wizard
        user.player.save()
