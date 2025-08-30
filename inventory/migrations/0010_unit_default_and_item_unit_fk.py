from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0009_unit"),
    ]

    operations = [
        migrations.AddField(
            model_name="unit",
            name="is_default",
            field=models.BooleanField(default=False),
        ),
        migrations.RenameField(
            model_name="item",
            old_name="unit_id",
            new_name="unit",
        ),
        migrations.AlterField(
            model_name="item",
            name="unit",
            field=models.ForeignKey(
                on_delete=models.PROTECT,
                related_name="items",
                db_column="unit_id",
                to="inventory.unit",
            ),
        ),
    ]

