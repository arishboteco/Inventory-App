from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0014_alter_item_is_active"),
    ]

    operations = [
        migrations.AlterField(
            model_name="recipe",
            name="tags",
            field=models.JSONField(blank=True, null=True, default=list),
        ),
    ]
