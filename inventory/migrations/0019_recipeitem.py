# Custom migration for RecipeItem
import django.db.models.deletion
import inventory.models.fields
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0018_indentpolink"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Only create the new RecipeItem table
        migrations.CreateModel(
            name="RecipeItem",
            fields=[
                (
                    "id",
                    models.AutoField(
                        db_column="recipe_item_id", primary_key=True, serialize=False
                    ),
                ),
                (
                    "quantity",
                    inventory.models.fields.CoerceFloatField(
                        blank=True,
                        decimal_places=2,
                        default=Decimal("0"),
                        max_digits=10,
                        null=True,
                    ),
                ),
                ("unit", models.CharField(blank=True, max_length=50, null=True)),
                (
                    "loss_pct",
                    inventory.models.fields.CoerceFloatField(
                        blank=True,
                        decimal_places=2,
                        default=Decimal("0"),
                        max_digits=10,
                        null=True,
                    ),
                ),
                ("sort_order", models.IntegerField(blank=True, null=True)),
                ("notes", models.TextField(blank=True, default="", null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "item",
                    models.ForeignKey(
                        db_column="item_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="recipe_usages",
                        to="inventory.item",
                    ),
                ),
                (
                    "recipe",
                    models.ForeignKey(
                        db_column="recipe_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="inventory.recipe",
                    ),
                ),
            ],
            options={
                "db_table": "recipe_items_new",
                "managed": True,
                "unique_together": {("recipe", "item")},
            },
        ),
    ]