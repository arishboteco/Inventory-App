from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0033_fix_recipe_items_new_columns"),
    ]

    operations = [
        migrations.CreateModel(
            name="SiteConfig",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                (
                    "business_name",
                    models.CharField(
                        default="Inventory Pro",
                        help_text="Displayed in page headers and reports.",
                        max_length=100,
                    ),
                ),
                (
                    "currency_symbol",
                    models.CharField(
                        default="$",
                        help_text="Prefix used for all monetary values (e.g. $, £, €, ₹).",
                        max_length=5,
                    ),
                ),
                (
                    "default_food_cost_target",
                    models.DecimalField(
                        decimal_places=2,
                        default=30,
                        help_text="Default target food cost % used in recipe costing.",
                        max_digits=5,
                    ),
                ),
            ],
            options={
                "verbose_name": "Site Configuration",
                "db_table": "site_config",
                "managed": True,
            },
        ),
    ]
