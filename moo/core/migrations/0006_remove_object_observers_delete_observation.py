# Generated by Django 4.2.7 on 2023-12-17 17:32

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_verbname_unique_verb_name"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="object",
            name="observers",
        ),
        migrations.DeleteModel(
            name="Observation",
        ),
    ]
