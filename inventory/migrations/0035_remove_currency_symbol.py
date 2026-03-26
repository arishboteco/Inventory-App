from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0034_siteconfig"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="siteconfig",
            name="currency_symbol",
        ),
    ]
