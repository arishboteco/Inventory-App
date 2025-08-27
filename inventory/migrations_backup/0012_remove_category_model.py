from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0011_auto_20250822_2123"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="item",
            name="category",
        ),
        migrations.RemoveField(
            model_name="item",
            name="sub_category",
        ),
        migrations.DeleteModel(
            name="Category",
        ),
        migrations.AddField(
            model_name="item",
            name="category_id",
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
