# Generated by Django 5.0 on 2024-02-11 15:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_remove_object_observers_delete_observation"),
    ]

    operations = [
        migrations.AddField(
            model_name="property",
            name="inherited",
            field=models.BooleanField(default=False),
        ),
    ]
