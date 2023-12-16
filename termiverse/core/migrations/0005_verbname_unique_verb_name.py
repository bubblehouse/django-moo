# Generated by Django 4.2.7 on 2023-12-16 19:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_accessibleobject_accessibleproperty_accessibleverb_and_more'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='verbname',
            constraint=models.UniqueConstraint(models.F('verb'), models.F('name'), name='unique_verb_name'),
        ),
    ]
