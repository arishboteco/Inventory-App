from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0008_remove_stocktransaction_related_po_id_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Category",
            fields=[
                ("category_id", models.AutoField(primary_key=True, serialize=False)),
                ("category", models.TextField()),
                ("sub_category", models.TextField()),
            ],
            options={
                "db_table": "category",
                "managed": False,
            },
        ),
        migrations.CreateModel(
            name="Unit",
            fields=[
                ("purchase_unit", models.TextField()),
                ("base_unit", models.TextField()),
                (
                    "conversion_factor",
                    models.DecimalField(decimal_places=6, max_digits=18),
                ),
                ("unit_id", models.AutoField(primary_key=True, serialize=False)),
            ],
            options={
                "db_table": "units",
                "managed": False,
            },
        ),
    ]
