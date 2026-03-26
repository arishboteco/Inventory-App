from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0035_remove_currency_symbol"),
    ]

    operations = [
        migrations.AddField(
            model_name="siteconfig",
            name="quantity_decimal_places",
            field=models.IntegerField(
                choices=[(0, "0"), (1, "1"), (2, "2"), (3, "3"), (4, "4")],
                default=2,
                help_text="Number of decimal places shown for stock quantities and conversion factors.",
            ),
        ),
    ]
