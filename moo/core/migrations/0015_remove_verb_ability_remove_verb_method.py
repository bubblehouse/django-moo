# Generated by Django 5.1.4 on 2025-05-04 14:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_alter_prepositionname_preposition'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='verb',
            name='ability',
        ),
        migrations.RemoveField(
            model_name='verb',
            name='method',
        ),
    ]
