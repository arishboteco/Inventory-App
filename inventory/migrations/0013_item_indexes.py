from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0012_alter_goodsreceivednote_notes_and_more"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="item",
            index=models.Index(fields=["name"], name="item_name_idx"),
        ),
        migrations.AddIndex(
            model_name="item",
            index=models.Index(fields=["current_stock"], name="item_cstock_idx"),
        ),
        migrations.AddIndex(
            model_name="item",
            index=models.Index(fields=["reorder_point"], name="item_rop_idx"),
        ),
        migrations.AddIndex(
            model_name="item",
            index=models.Index(fields=["is_active"], name="item_active_idx"),
        ),
    ]
