import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0041_savings_ledger"),
    ]

    operations = [
        migrations.CreateModel(
            name="VendorItemPrice",
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
                ("price", models.DecimalField(decimal_places=2, max_digits=12)),
                ("effective_from", models.DateField(db_index=True)),
                ("source", models.CharField(blank=True, default="", max_length=60)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="inventory.item"
                    ),
                ),
                (
                    "unit",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="inventory.unit",
                    ),
                ),
                (
                    "vendor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="inventory.supplier",
                    ),
                ),
            ],
            options={
                "db_table": "vendor_item_prices",
                "ordering": ["-effective_from", "-id"],
                "indexes": [
                    models.Index(fields=["vendor", "item"], name="vip_vendor_item_idx"),
                    models.Index(
                        fields=["item", "effective_from"], name="vip_item_eff_idx"
                    ),
                    models.Index(fields=["is_active"], name="vip_active_idx"),
                ],
            },
        ),
    ]
