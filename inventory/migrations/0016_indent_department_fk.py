from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0015_department_dept_name_idx_and_more"),
    ]

    operations = [
        # Database may already have department_id (FK). Apply state change without DB DDL.
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
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
            ],
        )
    ]
