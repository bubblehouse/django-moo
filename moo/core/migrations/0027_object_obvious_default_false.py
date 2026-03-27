from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0026_remove_task_origin_remove_task_user_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="object",
            name="obvious",
            field=models.BooleanField(default=False),
        ),
    ]
