from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0021_stock_transaction_reason_category_backdate"),
    ]

    operations = [
        migrations.CreateModel(
            name="StockSnapshot",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("snapshot_date", models.DateField(db_index=True)),
                ("quantity", models.DecimalField(decimal_places=4, max_digits=12)),
                (
                    "value",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=14, null=True
                    ),
                ),
                (
                    "item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="snapshots",
                        to="inventory.item",
                    ),
                ),
            ],
            options={
                "db_table": "stock_snapshots",
                "ordering": ["snapshot_date"],
                "unique_together": {("item", "snapshot_date")},
            },
        ),
    ]
