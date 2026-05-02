from django.contrib.auth.models import User  # pylint: disable=imported-auth-user
from django.core.management.base import BaseCommand, CommandError

from moo.core.models.auth import UniversalWizard


class Command(BaseCommand):
    help = "Mark or unmark a Django user as a universal wizard (cross-universe wizard rights)."

    def add_arguments(self, parser):
        parser.add_argument("username", type=str, help="The Django username.")
        parser.add_argument(
            "--remove",
            action="store_true",
            default=False,
            help="Revoke universal wizard status instead of granting it.",
        )

    def handle(self, *args, username=None, remove=False, **options):
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist as exc:
            raise CommandError(f"No such user: {username}") from exc

        if remove:
            deleted, _ = UniversalWizard.objects.filter(user=user).delete()
            if deleted:
                self.stdout.write(self.style.SUCCESS(f"Revoked universal wizard from '{username}'."))
            else:
                self.stdout.write(f"'{username}' was not a universal wizard.")
            return

        _, created = UniversalWizard.objects.get_or_create(user=user)
        if created:
            self.stdout.write(self.style.SUCCESS(f"Granted universal wizard to '{username}'."))
        else:
            self.stdout.write(f"'{username}' is already a universal wizard.")
