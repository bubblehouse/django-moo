# Generated manually for performance improvements
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0022_delete_accessibleobject_delete_accessibleproperty_and_more"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="property",
            index=models.Index(fields=["origin", "name"], name="property_origin_name_idx"),
        ),
        migrations.AddIndex(
            model_name="access",
            index=models.Index(fields=["object", "permission"], name="access_object_permission_idx"),
        ),
        migrations.AddIndex(
            model_name="access",
            index=models.Index(fields=["verb", "permission"], name="access_verb_permission_idx"),
        ),
        migrations.AddIndex(
            model_name="access",
            index=models.Index(fields=["property", "permission"], name="access_property_permission_idx"),
        ),
        migrations.AddIndex(
            model_name="player",
            index=models.Index(fields=["avatar", "wizard"], name="player_avatar_wizard_idx"),
        ),
    ]
