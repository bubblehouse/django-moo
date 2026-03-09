# Generated manually for ancestor cache denormalization
from collections import deque

from django.db import migrations, models
import django.db.models.deletion


def populate_ancestor_cache(apps, schema_editor):
    """
    Populate AncestorCache from existing Relationship data.
    For each object, perform a BFS over the Relationship table to find all ancestors
    with their depth (1 = direct parent) and path_weight (weight of the depth-1 link).
    """
    Object = apps.get_model("core", "Object")
    Relationship = apps.get_model("core", "Relationship")
    AncestorCache = apps.get_model("core", "AncestorCache")

    all_obj_pks = list(Object.objects.values_list("id", flat=True))

    # Load all relationships into memory for efficient traversal.
    parent_map = {}  # child_pk -> [(parent_pk, weight)]
    for rel in Relationship.objects.values("child_id", "parent_id", "weight"):
        parent_map.setdefault(rel["child_id"], []).append(
            (rel["parent_id"], rel["weight"])
        )

    rows = []
    for obj_pk in all_obj_pks:
        seen = {}  # ancestor_pk -> (depth, path_weight)
        queue = deque()
        for parent_pk, weight in parent_map.get(obj_pk, []):
            queue.append((parent_pk, 1, weight))

        while queue:
            ancestor_pk, depth, path_weight = queue.popleft()
            if ancestor_pk not in seen:
                seen[ancestor_pk] = (depth, path_weight)
                # Carry path_weight from depth-1 link as we climb further.
                for gp_pk, _ in parent_map.get(ancestor_pk, []):
                    if gp_pk not in seen:
                        queue.append((gp_pk, depth + 1, path_weight))

        for ancestor_pk, (depth, path_weight) in seen.items():
            rows.append(AncestorCache(
                descendant_id=obj_pk,
                ancestor_id=ancestor_pk,
                depth=depth,
                path_weight=path_weight,
            ))

        if len(rows) >= 500:
            AncestorCache.objects.bulk_create(rows, ignore_conflicts=True)
            rows = []

    if rows:
        AncestorCache.objects.bulk_create(rows, ignore_conflicts=True)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0024_covering_indexes"),
    ]

    operations = [
        migrations.CreateModel(
            name="AncestorCache",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("depth", models.IntegerField()),
                ("path_weight", models.IntegerField()),
                (
                    "ancestor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ancestor_descendants",
                        to="core.object",
                    ),
                ),
                (
                    "descendant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ancestor_cache",
                        to="core.object",
                    ),
                ),
            ],
            options={
                "unique_together": {("descendant", "ancestor")},
            },
        ),
        migrations.AddIndex(
            model_name="ancestorcache",
            index=models.Index(
                fields=["descendant", "depth", "path_weight"],
                name="ancestorcache_desc_depth_weight_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="ancestorcache",
            index=models.Index(
                fields=["ancestor"],
                name="ancestorcache_ancestor_idx",
            ),
        ),
        migrations.RunPython(populate_ancestor_cache, migrations.RunPython.noop),
    ]
