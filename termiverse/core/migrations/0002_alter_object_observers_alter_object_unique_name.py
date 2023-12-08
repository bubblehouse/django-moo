# Generated by Django 4.2.5 on 2023-11-27 02:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='object',
            name='observers',
            field=models.ManyToManyField(blank=True, related_name='observations', through='core.Observation', to='core.object'),
        ),
        migrations.AlterField(
            model_name='object',
            name='unique_name',
            field=models.BooleanField(default=False),
        ),
    ]