from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0017_goodsreceivednote_attachment"),
    ]

    operations = [
        migrations.CreateModel(
            name="IndentPOLink",
            fields=[
                ("link_id", models.AutoField(primary_key=True, serialize=False)),
                (
                    "indent_item",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        db_column="indent_item_id",
                        related_name="po_links",
                        to="inventory.indentitem",
                    ),
                ),
                (
                    "po_item",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        db_column="po_item_id",
                        related_name="indent_links",
                        to="inventory.purchaseorderitem",
                    ),
                ),
                ("planned_qty", models.DecimalField(max_digits=10, decimal_places=2)),
            ],
            options={
                "db_table": "indent_po_links",
                "managed": True,
            },
        ),
    ]
