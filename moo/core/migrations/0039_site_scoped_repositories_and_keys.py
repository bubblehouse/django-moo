"""Scope dataset registrations and external keys to a Site.

A ``Repository`` row is shared by every universe that loads the dataset, so it
gains a ``sites`` relation recording where the dataset was loaded. An
``ExternalKey`` gains a ``site`` and becomes unique per Site, so two universes
that bootstrap the same dataset no longer resolve to each other's objects.

The migration also advances the ``django_site`` id sequence. Migration 0030
creates the default Site with an explicit primary key, which leaves the
PostgreSQL sequence behind it, so the first new Site insert fails.
"""

import django.db.models.deletion
from django.conf import settings
from django.core.management.color import no_style
from django.db import migrations, models


def backfill_external_key_sites(apps, schema_editor):
    """Give every existing key the Site of the Object it maps to, or the default Site."""
    ExternalKey = apps.get_model("core", "ExternalKey")
    default_site_id = getattr(settings, "SITE_ID", 1)
    for row in ExternalKey.objects.select_related("object").iterator():
        ExternalKey.objects.filter(pk=row.pk).update(site_id=row.object.site_id or default_site_id)


def backfill_repository_sites(apps, schema_editor):
    """Record each dataset on every Site that holds one of its verbs."""
    Repository = apps.get_model("core", "Repository")
    Verb = apps.get_model("core", "Verb")
    for repo in Repository.objects.all():
        site_ids = (
            Verb.objects.filter(repo=repo, origin__site__isnull=False)
            .values_list("origin__site_id", flat=True)
            .distinct()
        )
        repo.sites.add(*site_ids)


def reset_site_sequence(apps, schema_editor):
    """Move the Site id sequence past the highest existing id."""
    Site = apps.get_model("sites", "Site")
    connection = schema_editor.connection
    for sql in connection.ops.sequence_reset_sql(no_style(), [Site]):
        schema_editor.execute(sql)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0038_player_unique_identity_per_site"),
        ("sites", "0002_alter_domain_unique"),
    ]

    operations = [
        migrations.AddField(
            model_name="repository",
            name="sites",
            field=models.ManyToManyField(blank=True, related_name="repositories", to="sites.site"),
        ),
        migrations.RunPython(backfill_repository_sites, migrations.RunPython.noop),
        migrations.AddField(
            model_name="externalkey",
            name="site",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="external_keys",
                to="sites.site",
            ),
        ),
        migrations.RunPython(backfill_external_key_sites, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="externalkey",
            name="site",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="external_keys",
                to="sites.site",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="externalkey",
            name="externalkey_namespace_key_unique",
        ),
        migrations.AddConstraint(
            model_name="externalkey",
            constraint=models.UniqueConstraint(
                fields=("site", "namespace", "key"), name="externalkey_site_namespace_key_unique"
            ),
        ),
        migrations.RunPython(reset_site_sequence, migrations.RunPython.noop),
    ]
