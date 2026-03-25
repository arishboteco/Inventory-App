from django.db import migrations, models

# Old values that map to SUB-recipe semantics
_SUB_VALUES = {"PREP", "SAUCE", "BATCH", "OTHER"}


def _map_to_binary(apps, schema_editor):
    """Migrate freeform type labels to FINAL / SUB."""
    Recipe = apps.get_model("inventory", "Recipe")
    for recipe in Recipe.objects.all():
        recipe.type = "SUB" if recipe.type in _SUB_VALUES else "FINAL"
        recipe.save(update_fields=["type"])


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0030_phase_d_apply_schema"),
    ]

    operations = [
        migrations.RunPython(_map_to_binary, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="recipe",
            name="type",
            field=models.CharField(
                blank=False,
                choices=[("FINAL", "Final Recipe"), ("SUB", "Sub-Recipe")],
                default="FINAL",
                max_length=10,
                null=False,
            ),
        ),
    ]
