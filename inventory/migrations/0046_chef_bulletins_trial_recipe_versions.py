import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0045_stocktransaction_wastage_photo"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ChefBulletin",
            fields=[
                ("bulletin_id", models.AutoField(primary_key=True, serialize=False)),
                ("period_start", models.DateField(db_index=True)),
                ("period_end", models.DateField(db_index=True)),
                (
                    "alert_type",
                    models.CharField(
                        choices=[
                            (
                                "FOOD_COST_ABOVE_TARGET",
                                "Recipe food cost above target",
                            ),
                            (
                                "INGREDIENT_PRICE_INCREASED",
                                "Ingredient price increased",
                            ),
                            ("RECIPE_COST_CHANGED", "Recipe cost changed"),
                            ("HIGH_SALES_LOW_MARGIN", "High sales but low margin"),
                            ("ACTUAL_USAGE_ABOVE_IDEAL", "Actual usage above ideal"),
                        ],
                        max_length=40,
                    ),
                ),
                ("headline", models.CharField(blank=True, default="", max_length=255)),
                (
                    "current_food_cost_pct",
                    models.DecimalField(decimal_places=2, default=0, max_digits=6),
                ),
                (
                    "target_food_cost_pct",
                    models.DecimalField(decimal_places=2, default=0, max_digits=6),
                ),
                (
                    "monthly_sales",
                    models.DecimalField(decimal_places=2, default=0, max_digits=14),
                ),
                (
                    "unrealised_profit",
                    models.DecimalField(decimal_places=2, default=0, max_digits=14),
                ),
                ("main_cost_drivers", models.JSONField(blank=True, default=list)),
                ("suggested_change", models.TextField(blank=True, default="")),
                (
                    "expected_saving",
                    models.DecimalField(decimal_places=2, default=0, max_digits=14),
                ),
                (
                    "risk_level",
                    models.CharField(
                        choices=[
                            ("LOW", "Low"),
                            ("MEDIUM", "Medium"),
                            ("HIGH", "High"),
                        ],
                        default="MEDIUM",
                        max_length=10,
                    ),
                ),
                (
                    "chef_decision",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("APPROVE_TRIAL", "Approve trial"),
                            ("MODIFY", "Modify"),
                            ("REJECT", "Reject"),
                            ("SEND_TO_OWNER", "Send to owner"),
                        ],
                        default="PENDING",
                        max_length=20,
                    ),
                ),
                ("decision_notes", models.TextField(blank=True, default="")),
                ("decided_at", models.DateTimeField(blank=True, null=True)),
                ("is_open", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "decided_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "recipe",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="chef_bulletins",
                        to="inventory.recipe",
                    ),
                ),
            ],
            options={
                "db_table": "chef_bulletins",
                "ordering": ["-expected_saving", "-updated_at"],
            },
        ),
        migrations.CreateModel(
            name="TrialRecipeVersion",
            fields=[
                ("trial_id", models.AutoField(primary_key=True, serialize=False)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("DRAFT", "Draft"),
                            ("UNDER_REVIEW", "Under review"),
                            ("APPROVED", "Approved"),
                            ("REJECTED", "Rejected"),
                        ],
                        default="DRAFT",
                        max_length=20,
                    ),
                ),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "bulletin",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="trial_versions",
                        to="inventory.chefbulletin",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "source_recipe",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="trial_versions_source",
                        to="inventory.recipe",
                    ),
                ),
                (
                    "trial_recipe",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="trial_versions_generated",
                        to="inventory.recipe",
                    ),
                ),
            ],
            options={
                "db_table": "trial_recipe_versions",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="chefbulletin",
            index=models.Index(
                fields=["recipe", "alert_type"], name="chef_bul_recipe_alert_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="chefbulletin",
            index=models.Index(
                fields=["is_open", "risk_level"], name="chef_bul_open_risk_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="chefbulletin",
            index=models.Index(
                fields=["period_start", "period_end"], name="chef_bul_period_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="trialrecipeversion",
            index=models.Index(
                fields=["bulletin", "status"], name="trial_ver_bulletin_status_idx"
            ),
        ),
    ]
