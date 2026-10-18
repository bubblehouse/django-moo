from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0040_player_muted_until"),
    ]

    operations = [
        migrations.AlterField(
            model_name="auditlog",
            name="action",
            field=models.CharField(
                choices=[
                    ("create", "create"),
                    ("recycle", "recycle"),
                    ("destroy", "destroy"),
                    ("restore", "restore"),
                    ("owner_change", "owner_change"),
                    ("permission_change", "permission_change"),
                    ("suspend", "suspend"),
                    ("unsuspend", "unsuspend"),
                    ("ban", "ban"),
                    ("unban", "unban"),
                    ("mute", "mute"),
                    ("unmute", "unmute"),
                    ("report", "report"),
                ],
                max_length=24,
            ),
        ),
    ]
