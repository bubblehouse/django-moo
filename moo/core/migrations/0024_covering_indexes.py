# Generated manually for performance improvements
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0023_perf_indexes"),
    ]

    operations = [
        # Covering composite on Relationship(child, parent, weight) so the recursive
        # CTE can satisfy both the base-case WHERE child_id=? and the path columns
        # (parent_id, weight) from a single index scan without a heap fetch.
        migrations.AddIndex(
            model_name="relationship",
            index=models.Index(
                fields=["child", "parent", "weight"],
                name="relationship_child_parent_weight_idx",
            ),
        ),
        # Composite on VerbName(name, verb) — reversed order from the existing unique
        # constraint on (verb, name) — so PostgreSQL can start from the name filter
        # when the CTE joins VerbName on names__name=? during verb dispatch.
        migrations.AddIndex(
            model_name="verbname",
            index=models.Index(
                fields=["name", "verb"],
                name="verbname_name_verb_idx",
            ),
        ),
    ]
