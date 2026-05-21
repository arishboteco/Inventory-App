from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0046_chef_bulletins_trial_recipe_versions"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="RecoveryAction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                (
                    "leakage_type",
                    models.CharField(
                        choices=[
                            ("FOOD_COST_GAP", "Food cost gap"),
                            ("VENDOR_PRICE", "Vendor price"),
                            ("INVOICE_MISMATCH", "Invoice mismatch"),
                            ("RECIPE_OPTIMISATION", "Recipe optimisation"),
                            ("WASTE_REDUCTION", "Waste reduction"),
                            ("VARIANCE_REDUCTION", "Variance reduction"),
                            ("MENU_PRICE_CORRECTION", "Menu price correction"),
                        ],
                        max_length=40,
                    ),
                ),
                ("expected_saving", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("due_date", models.DateField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("SUGGESTED", "Suggested"),
                            ("ASSIGNED", "Assigned"),
                            ("IN_PROGRESS", "In progress"),
                            ("IMPLEMENTED", "Implemented"),
                            ("VERIFIED", "Verified"),
                            ("REJECTED", "Rejected"),
                        ],
                        default="SUGGESTED",
                        max_length=16,
                    ),
                ),
                ("implemented_date", models.DateField(blank=True, null=True)),
                ("verified_saving", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "assigned_to",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="recovery_actions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "linked_chef_bulletin",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="recovery_actions",
                        to="inventory.chefbulletin",
                    ),
                ),
                (
                    "linked_item",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="recovery_actions",
                        to="inventory.item",
                    ),
                ),
                (
                    "linked_savings_entries",
                    models.ManyToManyField(blank=True, related_name="recovery_actions", to="inventory.savingsledger"),
                ),
            ],
            options={
                "db_table": "recovery_actions",
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.AddIndex(
            model_name="recoveryaction",
            index=models.Index(fields=["status"], name="rec_action_status_idx"),
        ),
        migrations.AddIndex(
            model_name="recoveryaction",
            index=models.Index(fields=["leakage_type"], name="rec_action_type_idx"),
        ),
        migrations.AddIndex(
            model_name="recoveryaction",
            index=models.Index(fields=["due_date"], name="rec_action_due_idx"),
        ),
        migrations.AddIndex(
            model_name="recoveryaction",
            index=models.Index(fields=["assigned_to", "status"], name="rec_action_assign_status_idx"),
        ),
    ]
