from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0031_universal_wizard"),
    ]

    operations = [
        migrations.AddField(
            model_name="object",
            name="_initialized",
            field=models.BooleanField(default=False),
        ),
    ]
