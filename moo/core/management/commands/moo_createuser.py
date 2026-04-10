# pylint: disable=imported-auth-user
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from moo.core.models import Object, Player


class Command(BaseCommand):
    help = "Create a Django user and a linked MOO player object in one step."

    def add_arguments(self, parser):
        parser.add_argument("username", type=str, help="Django login username.")
        parser.add_argument("avatar", type=str, help="In-world name for the MOO player object.")
        parser.add_argument("--password", type=str, default=None, help="Password (prompted if omitted).")
        parser.add_argument(
            "--wizard",
            action="store_true",
            help="Grant wizard (game admin) privileges inside the MOO.",
        )

    def handle(self, username, avatar, password=None, wizard=False, **kwargs):  # pylint: disable=arguments-differ
        if User.objects.filter(username=username).exists():
            raise CommandError(f"Django user '{username}' already exists.")
        if Object.objects.filter(name=avatar, unique_name=True).exists():
            raise CommandError(f"MOO object '{avatar}' already exists.")

        if password is None:
            import getpass
            password = getpass.getpass(f"Password for {username}: ")

        user = User.objects.create_user(username=username, password=password)

        system = Object.objects.get(id=1)
        parent_class = system.get_property("wizard" if wizard else "player")
        avatar_obj = Object(name=avatar, unique_name=True)
        avatar_obj.save()
        avatar_obj.parents.add(parent_class)
        avatar_obj.owner = avatar_obj
        avatar_obj.save()

        Player.objects.create(user=user, avatar=avatar_obj, wizard=wizard)

        self.stdout.write(self.style.SUCCESS(
            f"Created user '{username}' with MOO avatar '{avatar}' (#{avatar_obj.pk})"
            + (" [wizard]" if wizard else "")
        ))
