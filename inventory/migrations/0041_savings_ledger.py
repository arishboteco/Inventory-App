import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0040_align_not_null_with_models"),
    ]

    operations = [
        migrations.CreateModel(
            name="SavingsLedger",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("date", models.DateField(db_index=True)),
                ("outlet", models.CharField(blank=True, max_length=120, null=True)),
                (
                    "saving_type",
                    models.CharField(
                        choices=[
                            ("VENDOR_SAVING", "Vendor saving"),
                            ("INVOICE_MISMATCH_CAUGHT", "Invoice mismatch caught"),
                            ("RECIPE_OPTIMISATION", "Recipe optimisation"),
                            ("WASTE_REDUCTION", "Waste reduction"),
                            ("VARIANCE_REDUCTION", "Variance reduction"),
                            ("MENU_PRICE_CORRECTION", "Menu price correction"),
                        ],
                        max_length=40,
                    ),
                ),
                (
                    "source_document_type",
                    models.CharField(blank=True, default="", max_length=50),
                ),
                (
                    "source_document_id",
                    models.CharField(blank=True, default="", max_length=80),
                ),
                (
                    "baseline_price",
                    models.DecimalField(decimal_places=2, default=0, max_digits=12),
                ),
                (
                    "selected_price",
                    models.DecimalField(decimal_places=2, default=0, max_digits=12),
                ),
                (
                    "invoice_price",
                    models.DecimalField(decimal_places=2, default=0, max_digits=12),
                ),
                (
                    "quantity",
                    models.DecimalField(decimal_places=3, default=0, max_digits=12),
                ),
                (
                    "estimated_saving",
                    models.DecimalField(decimal_places=2, default=0, max_digits=14),
                ),
                (
                    "confirmed_saving",
                    models.DecimalField(decimal_places=2, default=0, max_digits=14),
                ),
                (
                    "lost_saving",
                    models.DecimalField(decimal_places=2, default=0, max_digits=14),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("ESTIMATED", "Estimated"),
                            ("CONFIRMED", "Confirmed"),
                            ("LOST", "Lost"),
                            ("REJECTED", "Rejected"),
                            ("VERIFIED", "Verified"),
                        ],
                        default="ESTIMATED",
                        max_length=16,
                    ),
                ),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "item",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="inventory.item",
                    ),
                ),
            ],
            options={
                "db_table": "savings_ledger",
                "ordering": ["-date", "-id"],
                "indexes": [
                    models.Index(fields=["date"], name="sav_ledger_date_idx"),
                    models.Index(fields=["status"], name="sav_ledger_status_idx"),
                    models.Index(fields=["saving_type"], name="sav_ledger_type_idx"),
                    models.Index(
                        fields=["item", "date"], name="sav_ledger_item_date_idx"
                    ),
                ],
            },
        ),
    ]
