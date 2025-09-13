from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="indent",
            name="department",
            field=models.ForeignKey(
                to="inventory.department",
                on_delete=models.PROTECT,
                db_column="department_id",
                blank=True,
                null=True,
            ),
        ),
    ]

